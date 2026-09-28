# -*- coding: utf-8 -*-
"""أداة بيانات Seed: توليد ملف عينة + استيراد شيت locations (Idempotent).

    python -m app.scripts.seed make [--out seed/sample_seed.xlsx]
    python -m app.scripts.seed load <xlsx>
"""
import argparse
import json
import os
import sys

from app.config import BACKEND_DIR, ensure_tools_on_path
from app.db.base import Base, SessionLocal, engine
from app.db import models  # noqa: F401  (تسجيل الجداول)
from app.services import locations as loc_service
from app.services.sheet import sheet_dicts

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


SEED_ROWS = [
    ["row_id", "code", "type", "parent_code", "name", "status", "updated_at"],
    [1, "PRJ-001", "PROJECT", "", "مشروع الرياض", "ACTIVE", "2026-09-20T08:00:00+03:00"],
    [2, "RGN-001", "REGION", "PRJ-001", "المنطقة الشرقية", "ACTIVE", "2026-09-20T08:01:00+03:00"],
    [3, "ZN-001", "ZONE", "RGN-001", "محطة الشمال", "ACTIVE", "2026-09-20T08:02:00+03:00"],
    [4, "ZN-002", "ZONE", "RGN-001", "محطة الجنوب", "ACTIVE", "2026-09-20T08:03:00+03:00"],
    [5, "LOC-001", "LOCATION", "ZN-001", "غرفة المضخات الرئيسية", "ACTIVE", "2026-09-20T08:04:00+03:00"],
    [6, "LOC-002", "LOCATION", "ZN-001", "غرفة الفلاتر", "ACTIVE", "2026-09-20T08:05:00+03:00"],
    [7, "LOC-003", "LOCATION", "ZN-002", "بئر رقم 3", "ACTIVE", "2026-09-20T08:06:00+03:00"],
]


def cmd_make(args):
    ensure_tools_on_path()
    import xlsx_min  # type: ignore

    out = args.out or str(BACKEND_DIR / "seed" / "sample_seed.xlsx")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    xlsx_min.write_workbook(out, [("locations", SEED_ROWS)])
    print("seed written:", out)
    return 0


def cmd_load(args):
    ensure_tools_on_path()
    import xlsx_min  # type: ignore

    Base.metadata.create_all(bind=engine)
    workbook = xlsx_min.read_workbook(args.path)
    rows = sheet_dicts(workbook.get("locations", []))
    db = SessionLocal()
    try:
        result = loc_service.seed_rows(db, rows)
    finally:
        db.close()
    print(json.dumps(result, ensure_ascii=False))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="ProTrack seed workbook tool")
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("make", help="توليد ملف عينة")
    m.add_argument("--out", default=None)
    l = sub.add_parser("load", help="استيراد شيت locations")
    l.add_argument("path")
    args = ap.parse_args(argv)
    if args.cmd == "make":
        return cmd_make(args)
    return cmd_load(args)


if __name__ == "__main__":
    sys.exit(main())
