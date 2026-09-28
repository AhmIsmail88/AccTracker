# -*- coding: utf-8 -*-
"""تهيئة الفحوص: قاعدة بيانات مؤقتة معزولة لكل تشغيل."""
import os
import tempfile

_TMP = tempfile.mkdtemp(prefix="protrack_tests_")
os.environ["PROTRAK_DATA_DIR"] = os.path.join(_TMP, "data")
os.environ["PROTRAK_DB"] = os.path.join(_TMP, "data", "test.db")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db.base import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402


def _reset():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        conn.exec_driver_sql(
            "CREATE VIRTUAL TABLE IF NOT EXISTS manual_chunk_fts "
            "USING fts5(text, manual_id UNINDEXED, tokenize='unicode61')"
        )
        conn.exec_driver_sql("DELETE FROM manual_chunk_fts")


@pytest.fixture()
def client():
    _reset()
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def db_session():
    _reset()
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
