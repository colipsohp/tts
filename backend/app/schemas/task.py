"""任务相关 Pydantic 模型。"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.voice import VoiceOut

TaskStatus = Literal["pending", "running", "succeeded", "failed"]


class TaskCreate(BaseModel):
    """创建 TTS 任务的请求体。"""

    voice_id: int
    text: str = Field(min_length=1)


class TtsTaskOut(BaseModel):
    """任务输出模型（含音色信息、状态、音频访问路径）。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    voice: VoiceOut
    text: str
    status: TaskStatus
    audio_url: str | None = None
    error_message: str | None = None
    duration_seconds: float | None = None
    created_at: datetime
    completed_at: datetime | None = None

    @classmethod
    def from_orm_with_url(cls, obj: object, audio_url: str | None) -> "TtsTaskOut":
        """从 ORM 对象构造，注入音频访问路径。"""
        out = cls.model_validate(obj)
        out.audio_url = audio_url
        return out


class TaskOut(BaseModel):
    """任务创建后的简要输出（id + status 即可）。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    status: TaskStatus
