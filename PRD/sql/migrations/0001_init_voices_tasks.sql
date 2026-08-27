-- ============================================================
-- 0001_init_voices_tasks.sql
-- 背景：TTS 项目首次落地，创建音色表 voices 与任务表 tts_tasks。
-- 影响表：voices / tts_tasks
-- 幂等性：全部使用 CREATE TABLE IF NOT EXISTS / CREATE INDEX IF NOT EXISTS，
--         可重复执行，不会报错、不会改变结果。
-- 执行方式（SQLite）：
--   sqlite3 database/tts.db < PRD/sql/migrations/0001_init_voices_tasks.sql
-- 说明：应用启动时也会通过 SQLAlchemy create_all() 自动建表，本脚本用于
--       存量/其他环境手工同步。ORMs 只建新表不会补列，因此后续结构变更
--       必须追加新的增量脚本（ALTER TABLE ... ADD COLUMN IF NOT EXISTS）。
-- ============================================================

CREATE TABLE IF NOT EXISTS voices (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          VARCHAR NOT NULL,
    source_path   VARCHAR,
    is_builtin    BOOLEAN NOT NULL DEFAULT 1,
    gender        VARCHAR,
    fal_audio_url VARCHAR,
    sample_text   VARCHAR,
    is_favorite   BOOLEAN NOT NULL DEFAULT 0,
    last_used_at  DATETIME,
    created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_voices_name ON voices (name);

CREATE TABLE IF NOT EXISTS tts_tasks (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    voice_id         INTEGER NOT NULL REFERENCES voices (id),
    text             TEXT NOT NULL,
    status           VARCHAR NOT NULL DEFAULT 'pending',
    audio_path       VARCHAR,
    error_message    VARCHAR,
    duration_seconds FLOAT,
    created_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at     DATETIME
);

CREATE INDEX IF NOT EXISTS ix_tts_tasks_voice_id ON tts_tasks (voice_id);
CREATE INDEX IF NOT EXISTS ix_tts_tasks_status ON tts_tasks (status);
