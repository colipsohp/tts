# AGENTS.md — AI 编程公约

> 本文件是给 AI 编程助手（Copilot / Cursor / Codex 等）的项目级指令。
> **每次写或改代码前先读完本文件**，所有改动需符合以下约定。
> 人改了本文件 → AI 在下一次会话自动按新约定执行。

---

## 1. 项目定位（30 秒看懂）

一个简单的，利用fal.ai 提供的index tts 2 接口，将文字转为语音的小工具。

## 2.技术栈

| 层 | 技术 | 备注 |
|---|---|---|
| 后端 | **Python 3.12 + FastAPI + SQLAlchemy 2 + Pydantic v2** | >= 3.12，类型注解齐全 |
| 数据库 | 本地sqlite | 通过 Alembic 迁移 |
| 前端 | **Vue 3 + TypeScript + Vite** | `<script setup>` + Composition API |

## 3. 目录结构

```
backend/
  .venv/           # python虚拟环境
  app/             # 后端代码
    db/            # 数据库表定义， 数据库增删改查
  pyproject.toml   # uv 管理
  .env             # 本地配置（**不提交**）
frontend/
  src/             # 前端代码
PRD/               # 产品/技术文档
tests/             # 冒烟测试/临时排查脚本（统一放这里，**不要放 backend/ 根目录**）
logs/              # 调试/运行日志放 tests/logs/（**同样不要放 backend/**）
database/          # sqlite 数据库文件
assets/            # 项目资源文件，主要是音色文件
  tone/            # 音色文件
start/             # 项目前后端启动批处理文件，支持一键启动前后端
```

## 4. Python 编码规范

- **每个 .py 文件顶部必须有**：
  ```python
  """模块 docstring（一句话说清楚这个文件做什么）。
  
  可选：更详细的设计说明、注意事项。
  """
  from __future__ import annotations
  ```
- **类型注解齐全**：函数签名、变量、返回值都要标注；用 `X | None` 不用 `Optional[X]`
- **Pydantic v2**：用 `BaseModel` + `model_config = ConfigDict(from_attributes=True)`；不要用 v1 的 `Config` 类
- **SQLAlchemy 2 风格**：`Mapped[T]` + `mapped_column(...)`，不要用旧 `Column`
- **异常处理**：
  ```python
  except Exception as exc:  # noqa: BLE001
      logger.warning("...", exc)
  ```
  跨边界的失败要 **catch + 转 log**，绝不让单点失败炸整个任务/请求
- **配置走** `app/config.py` 的 `Settings` 类 + `@lru_cache get_settings()`；**不要在业务代码里直接 `os.environ.get`**
- **日志用** `logging.getLogger("vision_agent.<模块>")`；**不要 `print()`**

## 5. 配置项约定

- 写在 `backend/.env`（**绝不提交**），代码里读 `settings.XXX`
- **必须有默认值** + 字段类型在 `Settings` 类里明确
- 加新配置步骤：
  1. `config.py` 加字段 + 注释说明取值范围/单位
  2. `.env` 加示例 + 详细注释
  3. 用到的地方读 `settings.XXX`，不裸读 env
- 敏感字段（API key）**绝不出现在文档 / PRD / git 历史里**，用 `<placeholder>` 占位

## 6 数据库 / .env 改动同步约定（部署要求）

任何功能改动只要涉及**数据库结构**或 **`.env` 配置**，都必须同步产出可执行的增量脚本 / 清单，方便部署到其他环境（服务器 / 其他开发者机器）时一键同步，代码与数据/配置不脱节：

- **数据库改动** → 在 `PRD/sql/migrations/` 提供增量 SQL 脚本：
  - 命名：`NNNN_简短英文描述.sql`（如 `0009_logging.sql`），序号接现有最大编号 +1；
  - **必须幂等可重跑**：用 `CREATE TABLE IF NOT EXISTS` / `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` / `IF EXISTS` / `ON CONFLICT DO NOTHING` 等，重复执行不报错、不改出不同结果；
  - 脚本头注释写明：背景 / 影响表 / 执行方式（`psql -h <host> -U <user> -d <db> < 脚本.sql`）；
  - 提交前在本地 PG 实际跑一遍验证；
  - ⚠️ 纯 ORM 模型加字段不算完事：SQLAlchemy `create_all()` 只建新表、**不会给旧表补列**，必须显式 `ALTER TABLE ... ADD COLUMN IF NOT EXISTS ...`（幂等），见反模式。
- **.env 改动** → 在 `PRD/sql/env/` 提供**增量配置清单**：
  - 命名：`prdNN-简短描述.env`（如 `prd28-logging.env`）；
  - 内容 = 本次**新增**的配置项（键 = 示例值 + 注释，可直接 diff 后同步到各环境）；只列增量，不整文件复制；
  - 敏感字段（API key）写 `<placeholder>`，**绝不写真实值**；
  - 若顺手修复了既有配置（如 Windows 路径转义 bug），在文件末尾「注意」区说明。
- 本次改动既无 DB 也无 .env 变化 → 不需要这两个目录的产物。

## 7. 改动 SOP（每次都要做）

写或改代码时按这个顺序检查：

1. **先读上下文** —— 不假设、不臆测，相关文件至少读一遍再用 `replace_string_in_file`
2. **类型对齐** —— 后端改 schema → 前端 `types/index.ts` 同步
3. **加配置项** —— 不要在代码里硬编码常量，能配置的进 `config.py` + `.env`
4. **错误兜底** —— 沙箱 / 网络 / 模型调用都要 try/except + log
5. **运行验证** —— 用 `get_errors` 查编译错误；后端用 Pylance 或 `python -c "import app.main"`；前端 Vite 热更新
6. **不要提交** —— `.env` / `.venv` / `node_modules` / `.assets/` / `__pycache__/` 都在 `.gitignore`，**不要 force add**
7. **更新文档** —— 涉及架构变化要更新 `PRD/`；纯小改动可跳过

## 8. 文档优先级

| 文档 | 何时读 |
|---|---|
| **本文件 `AGENTS.md`** | 每次会话开始必读 |