"""应用配置：集中读取 backend/.env，业务代码统一通过 get_settings() 访问。

所有配置项必须有默认值 + 明确字段类型；敏感字段（FAL_KEY）只存在于 .env，绝不提交。
路径类配置默认相对项目根目录（backend/ 的上级目录）。
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# 项目根目录：backend/app/config.py -> backend -> 项目根
BASE_DIR = Path(__file__).resolve().parents[2]

# 把 .env 加载进 os.environ（fal_client 等第三方库依赖环境变量 FAL_KEY）
_ENV_FILE = BASE_DIR / "backend" / ".env"
if _ENV_FILE.exists():
    load_dotenv(_ENV_FILE, override=False)


class Settings(BaseSettings):
    """全局配置项。"""

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / "backend" / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ---- fal.ai ----
    # fal.ai API Key（必填，仅后端使用，绝不暴露到前端）
    fal_key: str = ""
    # 模型标识
    fal_model: str = "fal-ai/index-tts-2/text-to-speech"
    # 生成总超时（秒）：覆盖「排队 + 推理」全过程。Index TTS 2.0 推理可能
    # 需要 30~90 秒，加上 fal 队列等待，默认 300 秒避免任务被过早取消。
    fal_request_timeout: int = 300
    # 服务端开始处理前的超时（秒）：仅限制排队/路由等待上限，
    # 不限制推理时长（fal 侧语义，见 fal_client.subscribe 的 start_timeout）。
    fal_start_timeout: int = 120

    # ---- 目录 ----
    # 生成音频输出目录（相对项目根）
    output_dir: str = "workplace/generated"
    # 自定义音色上传目录（相对项目根）
    upload_dir: str = "workplace/uploads"
    # 内置音色扫描目录（相对项目根）
    voice_scan_dir: str = "assets/tone"
    # 数据库文件（相对项目根）
    database_url: str = "sqlite:///database/tts.db"

    # ---- 业务参数 ----
    # 单次文案最大字数
    max_text_length: int = 2000
    # 前端轮询间隔（秒）
    task_poll_interval: int = 2
    # 长时间卡在 running 的任务回收为 failed 的超时阈值（秒）
    stale_task_timeout: int = 3600
    # 上传音频大小上限（字节，50MB）
    max_upload_size: int = 50 * 1024 * 1024
    # 最近使用音色展示数量
    recent_voice_count: int = 10

    @property
    def output_dir_path(self) -> Path:
        """生成音频输出目录绝对路径（自动创建）。"""
        path = BASE_DIR / self.output_dir
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def upload_dir_path(self) -> Path:
        """自定义音色上传目录绝对路径（自动创建）。"""
        path = BASE_DIR / self.upload_dir
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def voice_scan_dir_path(self) -> Path:
        """内置音色扫描目录绝对路径。"""
        return BASE_DIR / self.voice_scan_dir

    @property
    def database_dir(self) -> Path:
        """数据库文件所在目录（自动创建）。"""
        path = BASE_DIR / "database"
        path.mkdir(parents=True, exist_ok=True)
        return path


@lru_cache
def get_settings() -> Settings:
    """获取全局配置（带 lru_cache，避免重复解析 .env）。"""
    return Settings()
