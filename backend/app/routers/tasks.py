"""任务 API 路由：创建 / 列表 / 详情 / 试听 / 下载 / 重新生成。"""

from __future__ import annotations

import logging
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, joinedload

from app.config import get_settings
from app.db import get_db
from app.db.models import TtsTask, Voice
from app.schemas.task import TaskCreate, TaskOut, TtsTaskOut
from app.services import tts_service, voice_service

logger = logging.getLogger("tts.routers.tasks")

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


def _audio_url(task_id: int) -> str | None:
    return f"/api/tasks/{task_id}/audio"


@router.post("", response_model=TtsTaskOut, status_code=201)
def create_task(payload: TaskCreate, db: Session = Depends(get_db)) -> TtsTaskOut:
    """创建 TTS 任务并后台异步生成。"""
    settings = get_settings()
    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="文字内容不能为空")
    if len(text) > settings.max_text_length:
        raise HTTPException(
            status_code=400,
            detail=f"文字长度超出限制（最多 {settings.max_text_length} 字，当前 {len(text)} 字）",
        )
    voice = db.get(Voice, payload.voice_id)
    if voice is None:
        raise HTTPException(status_code=400, detail="音色不存在")

    task = tts_service.create_task(db, TaskCreate(voice_id=voice.id, text=text))
    tts_service.schedule_task(task.id)
    return _to_out(db, task)


@router.get("", response_model=dict)
def list_tasks(
    search: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=30, ge=1, le=200),
    db: Session = Depends(get_db),
) -> dict:
    """历史任务列表（侧栏），按创建时间倒序。"""
    items, total = tts_service.list_tasks(db, search=search, page=page, page_size=page_size)
    return {"list": [_to_out(db, t) for t in items], "total": total}


@router.get("/{task_id}", response_model=TtsTaskOut)
def get_task(task_id: int, db: Session = Depends(get_db)) -> TtsTaskOut:
    """任务详情。"""
    task = db.get(TtsTask, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return _to_out(db, task)


@router.get("/{task_id}/audio")
def get_task_audio(task_id: int, db: Session = Depends(get_db)) -> FileResponse:
    """试听生成的音频（流式，支持 Range 拖动）。"""
    task = db.get(TtsTask, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    if not task.audio_path or task.status != "succeeded":
        raise HTTPException(status_code=404, detail="音频尚未生成")
    path = _resolve_audio_path(task)
    if path is None:
        raise HTTPException(status_code=404, detail="音频文件不存在")
    return FileResponse(path, media_type="audio/mpeg")


@router.get("/{task_id}/download")
def download_task_audio(task_id: int, db: Session = Depends(get_db)) -> FileResponse:
    """下载生成的音频（Content-Disposition: attachment）。"""
    task = db.get(TtsTask, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    if not task.audio_path or task.status != "succeeded":
        raise HTTPException(status_code=404, detail="音频尚未生成")
    path = _resolve_audio_path(task)
    if path is None:
        raise HTTPException(status_code=404, detail="音频文件不存在")
    filename = f"TTS_{task.id}_{_safe_name(task.voice.name)}.mp3"
    # RFC 5987 编码非 ASCII 文件名
    disposition = f"attachment; filename*=UTF-8''{quote(filename)}"
    return FileResponse(path, media_type="audio/mpeg", headers={"Content-Disposition": disposition})


@router.post("/{task_id}/regenerate", response_model=TtsTaskOut, status_code=201)
def regenerate(task_id: int, db: Session = Depends(get_db)) -> TtsTaskOut:
    """对同一音色 + 文案重新生成。"""
    old = db.get(TtsTask, task_id)
    if old is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    new_task = tts_service.regenerate(db, old.id)
    return _to_out(db, new_task)


def _to_out(db: Session, task: TtsTask) -> TtsTaskOut:
    """ORM → 输出模型：注入音色信息与音频访问路径。"""
    voice = db.get(Voice, task.voice_id)
    out = TtsTaskOut(
        id=task.id,
        voice=voice_service_voice_out(voice),
        text=task.text,
        status=task.status,  # type: ignore[arg-type]
        audio_url=_audio_url(task.id) if task.status == "succeeded" and task.audio_path else None,
        error_message=task.error_message,
        duration_seconds=task.duration_seconds,
        created_at=task.created_at,
        completed_at=task.completed_at,
    )
    return out


def voice_service_voice_out(voice: Voice | None):
    """Voice ORM → VoiceOut（from_attributes）。"""
    from app.schemas.voice import VoiceOut

    if voice is None:
        raise HTTPException(status_code=500, detail="任务关联音色缺失")
    return VoiceOut.model_validate(voice)


def _resolve_audio_path(task: TtsTask) -> Path | None:
    """解析任务音频绝对路径（audio_path 相对项目根）。"""
    if not task.audio_path:
        return None
    path = Path(task.audio_path)
    if not path.is_absolute():
        path = Path(__file__).resolve().parents[3] / path
    return path if path.exists() else None


def _safe_name(name: str) -> str:
    """文件名安全化：去非法字符，保留中文。"""
    return "".join(c for c in name if c not in r'\/:*?"<>|').strip() or "voice"
