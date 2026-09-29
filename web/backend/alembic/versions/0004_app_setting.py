"""إعدادات التطبيق — جدول app_setting (مفتاح/قيمة)

Revision ID: 0004_app_setting
Revises: 0003_cloud_import
Create Date: 2026-09-29
"""
from alembic import op

from app.db.base import Base
from app.db import models  # noqa: F401

revision = "0004_app_setting"
down_revision = "0003_cloud_import"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    # ينشئ الجدول الجديد فقط (checkfirst=True افتراضيًا): app_setting
    Base.metadata.create_all(bind=bind)


def downgrade():
    bind = op.get_bind()
    bind.exec_driver_sql("DROP TABLE IF EXISTS app_setting")
