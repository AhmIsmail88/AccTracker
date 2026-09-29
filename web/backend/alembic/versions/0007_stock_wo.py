"""المخزون وأوامر العمل — جداول spare_part / stock_movement / work_order / work_order_part (§20/§33)

Revision ID: 0007_stock_wo
Revises: 0006_ai_suggestion
Create Date: 2026-09-29
"""
from alembic import op

from app.db.base import Base
from app.db import models  # noqa: F401

revision = "0007_stock_wo"
down_revision = "0006_ai_suggestion"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    # ينشئ الجداول الجديدة فقط (checkfirst=True افتراضيًا)
    Base.metadata.create_all(bind=bind)


def downgrade():
    bind = op.get_bind()
    for table in ("work_order_part", "stock_movement", "work_order", "spare_part"):
        bind.exec_driver_sql("DROP TABLE IF EXISTS %s" % table)
