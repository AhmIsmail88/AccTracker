"""تحليل الصيانة بالذكاء الاصطناعي — جدول ai_suggestion (§11)

Revision ID: 0006_ai_suggestion
Revises: 0005_manual_ocr
Create Date: 2026-09-29
"""
from alembic import op

from app.db.base import Base
from app.db import models  # noqa: F401

revision = "0006_ai_suggestion"
down_revision = "0005_manual_ocr"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    # ينشئ الجدول الجديد فقط (checkfirst=True افتراضيًا): ai_suggestion
    Base.metadata.create_all(bind=bind)


def downgrade():
    bind = op.get_bind()
    bind.exec_driver_sql("DROP TABLE IF EXISTS ai_suggestion")
