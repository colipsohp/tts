"""数据库会话与引擎管理（SQLite + SQLAlchemy 2）。

提供 engine / SessionLocal / get_db 依赖；启动时通过 init_db() 建表（幂等）。
"""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.config import BASE_DIR, get_settings
from app.db.base import Base

settings = get_settings()

# SQLite 路径相对项目根解析（database_url 形如 sqlite:///database/tts.db）
_db_path = Path(settings.database_url.replace("sqlite:///", ""))
if not _db_path.is_absolute():
    _db_path = BASE_DIR / _db_path
_db_path.parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    f"sqlite:///{_db_path.as_posix()}",
    connect_args={"check_same_thread": False},
)


@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection: object, _connection_record: object) -> None:
    """SQLite 开启外键约束与 WAL 模式。"""
    cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def init_db() -> None:
    """建表（幂等，仅创建缺失的表，不会补列）。"""
    # 确保模型已导入注册到 Base.metadata
    import app.db.models  # noqa: F401

    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI 依赖：请求级数据库会话。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
