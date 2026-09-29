"""OCR — عمود ocr_pages على جدول manual

Revision ID: 0005_manual_ocr
Revises: 0004_app_setting
Create Date: 2026-09-29
"""
from alembic import op

revision = "0005_manual_ocr"
down_revision = "0004_app_setting"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    cols = {row[1] for row in bind.exec_driver_sql("PRAGMA table_info(manual)").fetchall()}
    if "ocr_pages" not in cols:
        bind.exec_driver_sql(
            "ALTER TABLE manual ADD COLUMN ocr_pages INTEGER NOT NULL DEFAULT 0"
        )


def downgrade():
    # SQLite القديم لا يدعم DROP COLUMN — نترك العمود (غير ضار)
    pass
