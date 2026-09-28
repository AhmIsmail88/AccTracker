# -*- coding: utf-8 -*-
"""إعدادات تطبيق ProTrack Web Backend."""
import os
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent          # web/backend/app
BACKEND_DIR = APP_DIR.parent                        # web/backend
REPO_ROOT = BACKEND_DIR.parent.parent               # repo root
CONTRACT_DIR = REPO_ROOT / "contract"
TOOLS_DIR = REPO_ROOT / "tools"

DATA_DIR = Path(os.environ.get("PROTRAK_DATA_DIR", str(BACKEND_DIR / "data")))
DB_PATH = Path(os.environ.get("PROTRAK_DB", str(DATA_DIR / "protrack.db")))
PHOTOS_DIR = DATA_DIR / "photos"


def ensure_dirs():
    for d in (DATA_DIR, PHOTOS_DIR):
        d.mkdir(parents=True, exist_ok=True)


def ensure_tools_on_path():
    """يضيف مجلد tools/ لمشروع المرحلة 0 إلى sys.path (لاستيراد الـvalidator المشترك)."""
    p = str(TOOLS_DIR)
    if p not in sys.path:
        sys.path.insert(0, p)


ensure_dirs()
