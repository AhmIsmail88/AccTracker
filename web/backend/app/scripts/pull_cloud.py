# -*- coding: utf-8 -*-
"""CLI: سحب الحزم الجديدة من السحابة واستيرادها.

الاستخدام:
    python -m app.scripts.pull_cloud
"""
import json
import sys

from app.db import models  # noqa: F401  (تسجيل الجداول)
from app.db.base import Base, SessionLocal, engine
from app.services.cloud_pull import CloudNotConfigured, pull_from_cloud

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def main():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        result = pull_from_cloud(db)
        if not result["results"]:
            print("لا توجد حزم جديدة في السحابة.")
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except CloudNotConfigured as exc:
        print("غير مُهيّأ: %s" % exc)
        return 2
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
