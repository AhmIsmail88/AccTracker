# -*- coding: utf-8 -*-
"""فحص أداة Seed: الاستيراد مرتين متطابق النتيجة (Idempotent)."""
from app.config import ensure_tools_on_path

ensure_tools_on_path()
import xlsx_min  # noqa: E402


def test_seed_idempotent(db_session, tmp_path):
    rows = [
        ["row_id", "code", "type", "parent_code", "name", "status", "updated_at"],
        [1, "PRJ-001", "PROJECT", "", "مشروع الرياض", "ACTIVE", "t"],
        [2, "RGN-001", "REGION", "PRJ-001", "المنطقة الشرقية", "ACTIVE", "t"],
        [3, "ZN-001", "ZONE", "RGN-001", "محطة الشمال", "ACTIVE", "t"],
        [4, "LOC-001", "LOCATION", "ZN-001", "غرفة المضخات", "ACTIVE", "t"],
    ]
    path = str(tmp_path / "seed.xlsx")
    xlsx_min.write_workbook(path, [("locations", rows)])

    from app.services import locations as svc
    from app.services.sheet import sheet_dicts

    data = sheet_dicts(xlsx_min.read_workbook(path).get("locations", []))
    r1 = svc.seed_rows(db_session, data)
    r2 = svc.seed_rows(db_session, data)
    assert r1 == {"created": 4, "skipped": 0}
    assert r2 == {"created": 0, "skipped": 4}
