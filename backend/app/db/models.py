"""ORM 模型定义：voices（音色表）与 tts_tasks（任务表）。

遵循 AGENTS.md：SQLAlchemy 2 风格 Mapped[T] + mapped_column；类型注解齐全。
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Voice(Base):
    """音色：内置音色（启动扫描 assets/tone）或用户上传的自定义音色。"""

    __tablename__ = "voices"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(index=True)
    source_path: Mapped[str | None] = mapped_column(default=None)
    is_builtin: Mapped[bool] = mapped_column(default=True)
    gender: Mapped[str | None] = mapped_column(default=None)
    fal_audio_url: Mapped[str | None] = mapped_column(default=None)
    sample_text: Mapped[str | None] = mapped_column(default=None)
    is_favorite: Mapped[bool] = mapped_column(default=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    tasks: Mapped[list["TtsTask"]] = relationship(back_populates="voice")


class TtsTask(Base):
    """TTS 生成任务：记录文案、状态、生成的音频路径与失败原因。"""

    __tablename__ = "tts_tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    voice_id: Mapped[int] = mapped_column(ForeignKey("voices.id"), index=True)
    text: Mapped[str]
    status: Mapped[str] = mapped_column(default="pending", index=True)
    audio_path: Mapped[str | None] = mapped_column(default=None)
    error_message: Mapped[str | None] = mapped_column(default=None)
    duration_seconds: Mapped[float | None] = mapped_column(default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)

    voice: Mapped[Voice] = relationship(back_populates="tasks")
