"""Phase Cloud — جدول cloud_import (سجل سحب الحزم من السحابة)

Revision ID: 0003_cloud_import
Revises: 0002_manuals
Create Date: 2026-09-29
"""
from alembic import op

from app.db.base import Base
from app.db import models  # noqa: F401

revision = "0003_cloud_import"
down_revision = "0002_manuals"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    # ينشئ الجدول الجديد فقط (checkfirst=True افتراضيًا): cloud_import
    Base.metadata.create_all(bind=bind)


def downgrade():
    bind = op.get_bind()
    bind.exec_driver_sql("DROP TABLE IF EXISTS cloud_import")
