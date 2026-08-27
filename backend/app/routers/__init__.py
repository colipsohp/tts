"""API 路由：音色 + 任务。"""

from __future__ import annotations

from app.routers.tasks import router as tasks_router
from app.routers.voices import router as voices_router

__all__ = ["voices_router", "tasks_router"]
