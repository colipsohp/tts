# TTS 后端服务

基于 fal.ai Index TTS 2.0 的文字转语音后端服务（FastAPI + SQLAlchemy 2 + Pydantic v2 + SQLite）。

## 快速开始

```bash
uv sync            # 安装依赖
uv run uvicorn app.main:app --reload --port 8000
```

## 环境变量

复制 `.env.example` 为 `.env` 并填写 `FAL_KEY`（fal.ai API Key，勿提交到 git）。
