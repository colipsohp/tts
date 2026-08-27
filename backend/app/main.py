"""FastAPI 应用入口：启动时建表 + 扫描内置音色 + 回收脏任务，注册 API 路由。"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db.session import SessionLocal, init_db
from app.routers import tasks_router, voices_router
from app.services import tts_service, voice_service

logger = logging.getLogger("tts.main")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """启动初始化：记录事件循环、建表、扫描内置音色、回收超时任务。"""
    tts_service.set_main_loop(asyncio.get_running_loop())
    init_db()
    try:
        with SessionLocal() as db:
            voice_service.scan_builtin_voices(db)
            tts_service.recycle_stale_tasks(db)
    except Exception as exc:  # noqa: BLE001
        logger.warning("启动初始化失败（继续启动）: %s", exc)
    yield


app = FastAPI(title="TTS 语音合成", version="0.1.0", lifespan=lifespan)

# 本地开发：允许前端 dev server 跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(voices_router)
app.include_router(tasks_router)


@app.get("/api/health", tags=["system"])
def health() -> dict[str, str]:
    """健康检查。"""
    return {"status": "ok"}


# 确保 get_settings 被调用（读取 .env 校验配置可加载）
_ = get_settings()
