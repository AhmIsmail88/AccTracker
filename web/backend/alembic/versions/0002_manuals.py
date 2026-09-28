"""Phase 3 — جداول الـManuals + فهرس FTS5

Revision ID: 0002_manuals
Revises: 0001_phase1
Create Date: 2026-09-28
"""
from alembic import op

from app.db.base import Base
from app.db import models  # noqa: F401

revision = "0002_manuals"
down_revision = "0001_phase1"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    # ينشئ الجداول الجديدة فقط (checkfirst=True افتراضيًا): manual / manual_section / manual_chunk / maintenance_rule
    Base.metadata.create_all(bind=bind)
    bind.exec_driver_sql(
        "CREATE VIRTUAL TABLE IF NOT EXISTS manual_chunk_fts "
        "USING fts5(text, manual_id UNINDEXED, tokenize='unicode61')"
    )


def downgrade():
    bind = op.get_bind()
    bind.exec_driver_sql("DROP TABLE IF EXISTS manual_chunk_fts")
    for table in ("maintenance_rule", "manual_chunk", "manual_section", "manual"):
        bind.exec_driver_sql("DROP TABLE IF EXISTS %s" % table)
