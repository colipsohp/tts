"""音色 API 路由：列表 / 上传自定义 / 试听 / 收藏。"""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.db.models import Voice
from app.schemas.voice import VoiceOut, VoicePage
from app.services import voice_service

logger = logging.getLogger("tts.routers.voices")

router = APIRouter(prefix="/api/voices", tags=["voices"])

_ALLOWED_UPLOAD_EXTS = {".wav", ".mp3", ".m4a"}


@router.get("", response_model=VoicePage)
def list_voices(
    search: str | None = Query(default=None),
    only_favorite: bool = Query(default=False),
    recent: int = Query(default=0, ge=0),
    gender: str | None = Query(default=None),
    is_builtin: bool | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
) -> VoicePage:
    """音色列表：支持搜索 / 只看星标 / 最近使用 / 性别 / 内置自定义过滤 / 分页。"""
    items, total = voice_service.list_voices(
        db,
        search=search,
        only_favorite=only_favorite,
        gender=gender,
        is_builtin=is_builtin,
        recent=recent,
        page=page,
        page_size=page_size,
    )
    return VoicePage(list=[VoiceOut.model_validate(v) for v in items], total=total)


@router.post("", response_model=VoiceOut, status_code=201)
async def create_voice(
    name: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> Voice:
    """上传自定义音色（wav/mp3/m4a，≤50MB）并注册。"""
    settings = get_settings()
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in _ALLOWED_UPLOAD_EXTS:
        raise HTTPException(status_code=400, detail=f"仅支持音频格式: {'/'.join(sorted(_ALLOWED_UPLOAD_EXTS))}")
    clean_name = voice_service.clean_voice_name(name)
    if not clean_name:
        raise HTTPException(status_code=400, detail="音色名称不能为空")

    data = await file.read()
    if len(data) > settings.max_upload_size:
        raise HTTPException(status_code=400, detail="音频文件超过 50MB 上限")
    if not data:
        raise HTTPException(status_code=400, detail="上传的音频文件为空")

    voice = voice_service.save_upload(db, clean_name, data, suffix)
    return voice


@router.post("/rescan", response_model=dict)
def rescan_builtin_voices(db: Session = Depends(get_db)) -> dict:
    """重新扫描 assets/tone/ 注册新增内置音色（幂等）。"""
    added = voice_service.scan_builtin_voices(db)
    return {"added": added}


@router.get("/{voice_id}/audio")
def get_voice_audio(voice_id: int, db: Session = Depends(get_db)) -> FileResponse:
    """试听参考音频（流式，支持 Range 拖动）。"""
    voice = db.get(Voice, voice_id)
    if voice is None:
        raise HTTPException(status_code=404, detail="音色不存在")
    path = voice_service.resolve_voice_path(voice)
    if path is None or not path.is_file():
        logger.warning("音色参考音频文件缺失: voice_id=%d path=%s", voice_id, voice.source_path)
        raise HTTPException(status_code=404, detail="参考音频文件不存在")
    media_type = _guess_media_type(path.suffix)
    return FileResponse(path, media_type=media_type)


@router.post("/{voice_id}/favorite")
def favorite(voice_id: int, db: Session = Depends(get_db)) -> dict[str, bool]:
    """收藏音色。"""
    voice = db.get(Voice, voice_id)
    if voice is None:
        raise HTTPException(status_code=404, detail="音色不存在")
    voice.is_favorite = True
    db.commit()
    return {"is_favorite": True}


@router.delete("/{voice_id}/favorite")
def unfavorite(voice_id: int, db: Session = Depends(get_db)) -> dict[str, bool]:
    """取消收藏音色。"""
    voice = db.get(Voice, voice_id)
    if voice is None:
        raise HTTPException(status_code=404, detail="音色不存在")
    voice.is_favorite = False
    db.commit()
    return {"is_favorite": False}


def _guess_media_type(suffix: str) -> str:
    """根据扩展名猜测音频 MIME 类型。"""
    return {
        ".wav": "audio/wav",
        ".mp3": "audio/mpeg",
        ".m4a": "audio/mp4",
        ".aac": "audio/aac",
        ".flac": "audio/flac",
        ".ogg": "audio/ogg",
    }.get(suffix.lower(), "application/octet-stream")
