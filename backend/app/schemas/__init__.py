"""Pydantic v2 请求/响应模型。"""

from __future__ import annotations

from app.schemas.task import TaskCreate, TaskOut, TaskStatus, TtsTaskOut
from app.schemas.voice import VoiceOut, VoicePage, VoiceCreate

__all__ = [
    "VoiceOut",
    "VoicePage",
    "VoiceCreate",
    "TaskCreate",
    "TaskOut",
    "TaskStatus",
    "TtsTaskOut",
]
