"""init voices and tasks

Revision ID: 0001
Revises:
Create Date: 2026-08-27
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """创建 voices / tts_tasks 表（幂等：已存在则跳过）。"""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = set(inspector.get_table_names())

    if "voices" not in existing:
        op.create_table(
            "voices",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("source_path", sa.String(), nullable=True),
            sa.Column("is_builtin", sa.Boolean(), nullable=False),
            sa.Column("gender", sa.String(), nullable=True),
            sa.Column("fal_audio_url", sa.String(), nullable=True),
            sa.Column("sample_text", sa.String(), nullable=True),
            sa.Column("is_favorite", sa.Boolean(), nullable=False),
            sa.Column("last_used_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        )
        op.create_index("ix_voices_name", "voices", ["name"])
        op.create_index("ix_voices_id", "voices", ["id"])

    if "tts_tasks" not in existing:
        op.create_table(
            "tts_tasks",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("voice_id", sa.Integer(), sa.ForeignKey("voices.id"), nullable=False),
            sa.Column("text", sa.Text(), nullable=False),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("audio_path", sa.String(), nullable=True),
            sa.Column("error_message", sa.String(), nullable=True),
            sa.Column("duration_seconds", sa.Float(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_tts_tasks_voice_id", "tts_tasks", ["voice_id"])
        op.create_index("ix_tts_tasks_status", "tts_tasks", ["status"])


def downgrade() -> None:
    """回滚：删除表（注意顺序：先子表后父表）。"""
    op.drop_index("ix_tts_tasks_status", table_name="tts_tasks")
    op.drop_index("ix_tts_tasks_voice_id", table_name="tts_tasks")
    op.drop_table("tts_tasks")
    op.drop_index("ix_voices_name", table_name="voices")
    op.drop_table("voices")
