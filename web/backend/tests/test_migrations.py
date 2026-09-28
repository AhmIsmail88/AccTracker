# -*- coding: utf-8 -*-
"""فحص ترحيلات Alembic: الترقية تنشئ كل الجداول على قاعدة جديدة."""
import os
import sqlite3
import subprocess
import sys

from app.config import BACKEND_DIR


def test_alembic_upgrade_creates_schema(tmp_path):
    db = str(tmp_path / "mig.db")
    env = dict(os.environ)
    env["PROTRAK_DATA_DIR"] = str(tmp_path)
    env["PROTRAK_DB"] = db
    r = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=str(BACKEND_DIR), env=env, capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    con = sqlite3.connect(db)
    try:
        tables = {row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    finally:
        con.close()
    expected = {
        "project", "region", "zone", "location", "hierarchy_conflict",
        "equipment", "equipment_event", "visit", "visit_equipment",
        "visit_checklist", "visit_photo", "imported_package",
    }
    assert expected.issubset(tables)
