"""音色相关 Pydantic 模型。"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class VoiceOut(BaseModel):
    """音色对外输出模型（与前端 types/index.ts 字段对齐）。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    is_builtin: bool
    gender: str | None
    is_favorite: bool
    last_used_at: datetime | None
    created_at: datetime
    source_path: str | None = None
    sample_text: str | None = None


class VoicePage(BaseModel):
    """音色分页列表。"""

    list: list[VoiceOut]
    total: int


class VoiceCreate(BaseModel):
    """创建自定义音色的请求（name 由 multipart 表单提供，此处仅做校验）。"""

    model_config = ConfigDict(from_attributes=True)

    name: str = Field(min_length=1, max_length=64)
