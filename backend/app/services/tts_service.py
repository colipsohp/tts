"""TTS 任务服务：任务创建、后台异步生成、状态流转、脏数据回收。

生成流程：pending → running → succeeded / failed；失败记录 error_message。
生成在独立线程池执行（fal_client.subscribe 为阻塞调用），每个后台任务使用独立 DB 会话。
"""

from __future__ import annotations

import asyncio
import logging
import subprocess
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.config import get_settings
from app.db.models import TtsTask, Voice
from app.db.session import SessionLocal
from app.schemas.task import TaskCreate
from app.services import fal_tts, voice_service

logger = logging.getLogger("tts.services.tts_service")

# 后台任务线程池（fal 阻塞调用不占事件循环）
_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="tts-task")
# 主事件循环引用：在 FastAPI startup 时捕获，供任意线程安全调度后台任务
_main_loop: asyncio.AbstractEventLoop | None = None


def set_main_loop(loop: asyncio.AbstractEventLoop) -> None:
    """记录主事件循环（启动时调用）。"""
    global _main_loop
    _main_loop = loop


def create_task(db: Session, payload: TaskCreate) -> TtsTask:
    """创建 TTS 任务（pending），并校验音色存在。"""
    voice = db.get(Voice, payload.voice_id)
    if voice is None:
        raise ValueError(f"音色不存在: voice_id={payload.voice_id}")
    task = TtsTask(voice_id=payload.voice_id, text=payload.text, status="pending")
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def schedule_task(task_id: int) -> None:
    """把任务调度到后台线程池执行（线程安全，可从任意线程调用）。

    loop.run_in_executor 内部走 call_soon_threadsafe，可在工作线程中安全调用。
    """
    loop = _main_loop or asyncio.get_event_loop()
    loop.run_in_executor(_executor, _run_task, task_id)


def regenerate(db: Session, task_id: int) -> TtsTask:
    """对同一 voice_id + text 重新发起任务（创建新任务并立即调度）。"""
    old = db.get(TtsTask, task_id)
    if old is None:
        raise ValueError(f"任务不存在: task_id={task_id}")
    new_task = create_task(db, TaskCreate(voice_id=old.voice_id, text=old.text))
    schedule_task(new_task.id)
    return new_task


def _run_task(task_id: int) -> None:
    """后台执行单个 TTS 任务（线程内，独立会话）。"""
    db = SessionLocal()
    try:
        task = db.get(TtsTask, task_id)
        if task is None:
            logger.warning("后台任务找不到记录，跳过: task_id=%d", task_id)
            return
        if task.status != "pending":
            logger.info("任务非 pending，跳过: task_id=%d status=%s", task_id, task.status)
            return

        task.status = "running"
        db.commit()
        _generate(db, task)
    except Exception as exc:  # noqa: BLE001
        logger.warning("任务执行异常: task_id=%d exc=%s", task_id, exc, exc_info=True)
        # FalTtsError 已是可读信息，直接透传；其它异常才标记为内部错误
        message = str(exc) if isinstance(exc, fal_tts.FalTtsError) else f"内部错误：{exc}"
        _mark_failed(db, task_id, message)
    finally:
        db.close()


def _generate(db: Session, task: TtsTask) -> None:
    """核心生成逻辑：fal 合成 → 落盘 → 更新状态。"""
    settings = get_settings()
    voice = db.get(Voice, task.voice_id)
    if voice is None:
        raise ValueError(f"音色不存在: voice_id={task.voice_id}")

    # 1. 取参考音频 URL（缓存 fal_audio_url，幂等）
    audio_url = voice_service.get_voice_audio_url(voice)

    # 2. fal 合成
    result_url = fal_tts.synthesize(
        audio_url, task.text, client_timeout=settings.fal_request_timeout
    )
    # 3. 下载到本地 workplace/generated/
    dest_dir = settings.output_dir_path
    local_path = fal_tts.download_audio(
        result_url, dest_dir, file_name=f"tts_{task.id}_{voice.id}.mp3"
    )

    # 4. 落库
    task.audio_path = str(local_path.relative_to(Path(__file__).resolve().parents[3]))
    task.status = "succeeded"
    task.completed_at = datetime.now(timezone.utc)
    task.duration_seconds = _probe_duration(local_path)
    voice.last_used_at = datetime.now(timezone.utc)
    db.commit()
    logger.info("任务完成: task_id=%d voice=%s", task.id, voice.name)


def _mark_failed(db: Session, task_id: int, message: str) -> None:
    """把任务置为 failed 并记录可读错误。"""
    task = db.get(TtsTask, task_id)
    if task is None:
        return
    task.status = "failed"
    task.error_message = message[:1000]
    task.completed_at = datetime.now(timezone.utc)
    db.commit()


def recycle_stale_tasks(db: Session, timeout_seconds: int | None = None) -> int:
    """把长时间卡住（running / pending）的脏数据回收为 failed（updated_at 超时）。返回回收数量。"""
    settings = get_settings()
    timeout = timeout_seconds or settings.stale_task_timeout
    threshold = datetime.now(timezone.utc) - timedelta(seconds=timeout)
    stale = list(
        db.scalars(
            select(TtsTask).where(
                TtsTask.status.in_(["running", "pending"]),
                TtsTask.updated_at < threshold,
            )
        ).all()
    )
    for task in stale:
        task.status = "failed"
        task.error_message = "生成超时，任务已自动标记为失败，请重试"
        task.completed_at = datetime.now(timezone.utc)
    if stale:
        db.commit()
        logger.info("回收 %d 个超时任务", len(stale))
    return len(stale)


def _probe_duration(path: Path) -> float | None:
    """尽力探测音频时长（依赖 ffprobe），不可用时返回 None。"""
    try:
        proc = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if proc.returncode == 0:
            return round(float(proc.stdout.strip()), 2)
    except Exception as exc:  # noqa: BLE001
        logger.debug("ffprobe 探测时长失败（忽略）: %s", exc)
    return None


def list_tasks(db: Session, search: str | None = None, page: int = 1, page_size: int = 30) -> tuple[list[TtsTask], int]:
    """历史任务列表（按创建时间倒序），含音色信息。"""
    stmt = select(TtsTask).options(joinedload(TtsTask.voice))
    if search:
        like = f"%{search}%"
        stmt = stmt.join(TtsTask.voice).where(
            TtsTask.text.like(like) | Voice.name.like(like)
        )
    total = len(db.scalars(stmt).all())
    stmt = stmt.order_by(TtsTask.created_at.desc(), TtsTask.id.desc())
    if page_size > 0:
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    items = list(db.scalars(stmt).all())
    return items, total
