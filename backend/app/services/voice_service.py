"""音色服务：内置音色扫描注册、自定义音色上传注册、音色查询、路径解析。

内置音色：启动时扫描 settings.voice_scan_dir_path（assets/tone/），按 name+source_path 幂等注册；
自定义音色：上传到 workplace/uploads/ 后注册。
"""

from __future__ import annotations

import logging
import re
import uuid
from pathlib import Path

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import Voice
from app.services import fal_tts

logger = logging.getLogger("tts.services.voice_service")

_AUDIO_EXTS = {".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg"}
_GENDER_FEMALE_WORDS = [
    "女", "姐", "妹", "妈", "奶", "萝莉", "少女", "御姐", "公主", "皇后", "娘",
    "姑姑", "婶", "婆", "夫人", "女生", "女孩", "小仙女", "甜心",
]
_GENDER_MALE_WORDS = [
    "男", "哥", "弟", "叔", "爷", "爸", "霸", "君", "少年", "先生", "叔音",
    "男人", "男孩", "老总", "师傅",
]


def clean_voice_name(stem: str) -> str:
    """清洗音色名：压缩多余空白、去掉首尾空白。"""
    name = re.sub(r"\s+", " ", stem).strip()
    return name


def guess_gender(stem: str) -> str | None:
    """从文件名启发式识别性别：male / female / unknown。"""
    if any(word in stem for word in _GENDER_FEMALE_WORDS):
        return "female"
    if any(word in stem for word in _GENDER_MALE_WORDS):
        return "male"
    return "unknown"


def scan_builtin_voices(db: Session) -> int:
    """扫描 assets/tone/ 并幂等注册内置音色，返回新增数量。

    已存在（name + source_path 匹配）的跳过；不删除本地已不存在的 DB 记录。
    """
    settings = get_settings()
    scan_dir = settings.voice_scan_dir_path
    if not scan_dir.exists():
        logger.warning("内置音色目录不存在，跳过扫描: %s", scan_dir)
        return 0

    added = 0
    for file_path in sorted(scan_dir.iterdir()):
        if not file_path.is_file():
            continue
        if file_path.name.lower() in {".gitkeep"}:
            continue
        if file_path.suffix.lower() not in _AUDIO_EXTS:
            continue

        stem = file_path.stem
        name = clean_voice_name(stem)
        if not name:
            continue
        # source_path：内置音色存相对 voice_scan_dir 的文件名
        rel = file_path.name
        exists = db.scalar(
            select(Voice).where(Voice.name == name, Voice.source_path == rel, Voice.is_builtin.is_(True))
        )
        if exists:
            continue
        db.add(
            Voice(
                name=name,
                source_path=rel,
                is_builtin=True,
                gender=guess_gender(stem),
            )
        )
        added += 1

    if added:
        db.commit()
        logger.info("内置音色扫描完成，新增 %d 个", added)
    return added


def resolve_voice_path(voice: Voice) -> Path | None:
    """把音色 source_path 解析为本地绝对路径。

    内置音色：相对 voice_scan_dir（assets/tone/）；自定义音色：相对项目根目录。
    """
    if not voice.source_path:
        return None
    settings = get_settings()
    if voice.is_builtin:
        path = settings.voice_scan_dir_path / voice.source_path
    else:
        path = Path(voice.source_path)
        if not path.is_absolute():
            path = Path(__file__).resolve().parents[3] / path  # 项目根
    return path if path.exists() else None


def list_voices(
    db: Session,
    search: str | None = None,
    only_favorite: bool = False,
    gender: str | None = None,
    is_builtin: bool | None = None,
    recent: int = 0,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[Voice], int]:
    """音色列表查询，支持搜索 / 只看星标 / 性别 / 内置自定义 / 最近使用 / 分页。"""
    stmt = select(Voice)

    # 最近使用模式：忽略其它过滤，直接返回最近使用的 N 个
    if recent and recent > 0:
        stmt = (
            stmt.where(Voice.last_used_at.is_not(None))
            .order_by(Voice.last_used_at.desc())
            .limit(recent)
        )
        return list(db.scalars(stmt).all()), 0

    if search:
        like = f"%{search}%"
        stmt = stmt.where(or_(Voice.name.like(like), Voice.sample_text.like(like)))
    if only_favorite:
        stmt = stmt.where(Voice.is_favorite.is_(True))
    if gender and gender != "unknown":
        stmt = stmt.where(Voice.gender == gender)
    elif gender == "unknown":
        stmt = stmt.where(Voice.gender.is_(None))
    if is_builtin is not None:
        stmt = stmt.where(Voice.is_builtin.is_(is_builtin))

    total = len(db.scalars(stmt).all())
    stmt = stmt.order_by(Voice.is_builtin.desc(), Voice.created_at.desc(), Voice.id.desc())
    if page_size > 0:
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    items = list(db.scalars(stmt).all())
    return items, total


def create_custom_voice(db: Session, name: str, file_path: Path) -> Voice:
    """注册自定义音色：文件已保存到 workplace/uploads/，落库并返回。

    参考音频的 fal 上传采用「首次使用时懒上传」策略（见 get_voice_audio_url），
    避免注册请求被网络阻塞，也保证 fal_audio_url 幂等缓存。
    """
    voice = Voice(
        name=clean_voice_name(name),
        source_path=str(file_path.relative_to(Path(__file__).resolve().parents[3])),
        is_builtin=False,
        gender=guess_gender(file_path.stem),
    )
    db.add(voice)
    db.commit()
    db.refresh(voice)
    return voice


def get_voice_audio_url(voice: Voice) -> str:
    """获取参考音频的 fal URL：优先缓存，否则上传并缓存（幂等）。"""
    if voice.fal_audio_url:
        return voice.fal_audio_url
    path = resolve_voice_path(voice)
    if path is None:
        raise FileNotFoundError(f"音色参考音频不存在: {voice.name}")
    url = fal_tts.upload_reference_audio(path)
    # 幂等缓存（并发场景下重复上传无害）
    voice.fal_audio_url = url
    return url


def save_upload(db: Session, name: str, data: bytes, suffix: str) -> Voice:
    """保存上传的自定义音色文件并注册。"""
    settings = get_settings()
    upload_dir = settings.upload_dir_path
    file_name = f"{uuid.uuid4().hex}{suffix.lower()}"
    file_path = upload_dir / file_name
    file_path.write_bytes(data)
    return create_custom_voice(db, name, file_path)
