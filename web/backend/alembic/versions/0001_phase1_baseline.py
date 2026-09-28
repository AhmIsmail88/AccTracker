"""Phase 1 baseline — كل جداول الويب

Revision ID: 0001_phase1
Revises:
Create Date: 2026-09-28
"""
from alembic import op

from app.db.base import Base
from app.db import models  # noqa: F401

revision = "0001_phase1"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Baseline: ننشئ نفس المخطط المعرّف في النماذج لضمان تطابق تام عند التأسيس.
    # المراجعات التالية (بعد Phase 1) تكون صريحة (op.create_table/op.add_column...).
    Base.metadata.create_all(bind=op.get_bind())


def downgrade():
    Base.metadata.drop_all(bind=op.get_bind())
