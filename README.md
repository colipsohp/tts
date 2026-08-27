# TTS 文字转语音工具

一个简单、本地化的文字转语音（TTS）小工具：选择音色（内置或上传参考音频自定义），输入文字，基于 fal.ai **Index TTS 2.0**（零样本语音克隆）生成自然语音，可试听与下载。

## 功能

- **内置音色库**：启动时自动扫描注册 `assets/tone/`（963+ 个参考音频）
- **自定义音色**：上传 10~30 秒干净人声（wav/mp3/m4a，≤50MB），零样本克隆
- **音色管理**：试听 / 收藏星标 / 只看星标 / 搜索 / 最近使用
- **任务系统**：异步生成、状态流转（pending→running→succeeded/failed）、失败重试、历史任务搜索
- **生成音频**：内嵌播放器试听、下载（支持 Range 拖动进度）

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | Python 3.12 + FastAPI + SQLAlchemy 2 + Pydantic v2 + SQLite |
| 前端 | Vue 3 + TypeScript + Vite + Element Plus |
| 语音 | fal.ai Index TTS 2.0（`fal-ai/index-tts-2/text-to-speech`） |

## 快速开始

### 1. 环境准备

- Python >= 3.12（推荐 [uv](https://docs.astral.sh/uv/) 管理）
- Node.js >= 18

### 2. 配置后端

```bash
cd backend
copy .env.example .env   # Windows
# 编辑 .env，填写 FAL_KEY（fal.ai API Key）
uv sync                   # 安装依赖
```

### 3. 启动

方式一（推荐）：双击运行 `start/start-all.bat`，或分别运行：

```bash
# 后端（端口 8000）
cd backend
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000

# 前端（端口 5173，代理 /api 到后端）
cd frontend
npm install
npm run dev
```

浏览器打开 http://localhost:5173

## 目录结构

```
backend/            # 后端（FastAPI + SQLAlchemy）
  app/
    config.py       # 配置（读取 backend/.env）
    db/             # 数据库模型与会话
    schemas/        # Pydantic 模型
    services/       # 音色 / fal / 任务服务
    routers/        # API 路由
  alembic/          # 数据库迁移
frontend/           # 前端（Vue 3 + TS + Vite）
  src/
    views/          # 首页 / 任务详情
    components/     # 侧栏 / 音色弹窗 / 播放器等
PRD/                # 产品/技术文档（含 sql 增量脚本）
tests/              # 冒烟测试
start/              # 一键启动脚本
database/           # SQLite 数据库文件
workplace/          # 运行产物（生成音频、上传音频）
assets/tone/        # 内置音色库
```

## API 概览

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/voices` | 音色列表（搜索/星标/最近/性别/内置自定义/分页） |
| POST | `/api/voices` | 上传自定义音色 |
| POST | `/api/voices/rescan` | 重新扫描内置音色 |
| GET | `/api/voices/{id}/audio` | 试听参考音频（Range） |
| POST/DELETE | `/api/voices/{id}/favorite` | 收藏 / 取消收藏 |
| POST | `/api/tasks` | 创建 TTS 任务 |
| GET | `/api/tasks` | 历史任务列表 |
| GET | `/api/tasks/{id}` | 任务详情 |
| GET | `/api/tasks/{id}/audio` | 试听生成音频（Range） |
| GET | `/api/tasks/{id}/download` | 下载生成音频 |
| POST | `/api/tasks/{id}/regenerate` | 重新生成 |

## 测试

```bash
# 启动后端后运行冒烟测试
uv run python tests/smoke_api.py
```

## 文档

- 产品需求：`PRD/1-项目总体需求.md`
- 数据库增量脚本：`PRD/sql/migrations/`
- 环境配置增量清单：`PRD/sql/env/`
