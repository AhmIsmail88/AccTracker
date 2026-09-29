# -*- coding: utf-8 -*-
"""إعدادات تطبيق AccTracker Web Backend — يعمل من الريبو أو من EXE مجمد."""
import os
import sys
from pathlib import Path

IS_FROZEN = bool(getattr(sys, "frozen", False))

APP_DIR = Path(__file__).resolve().parent          # web/backend/app (أو <bundle>/app داخل الـEXE)
BACKEND_DIR = APP_DIR.parent                        # web/backend

if IS_FROZEN:
    # داخل EXE: الموارد ملفات ثابتة في مجلد الاستخراج المؤقت (_MEIPASS)
    BUNDLE_DIR = Path(getattr(sys, "_MEIPASS", str(Path(sys.executable).resolve().parent)))
    REPO_ROOT = BUNDLE_DIR
    CONTRACT_DIR = BUNDLE_DIR / "contract"
    TOOLS_DIR = BUNDLE_DIR / "tools"
    ALEMBIC_DIR = BUNDLE_DIR / "alembic"
    ALEMBIC_INI = BUNDLE_DIR / "alembic.ini"
    FRONTEND_DIST = BUNDLE_DIR / "frontend_dist"
else:
    BUNDLE_DIR = BACKEND_DIR
    REPO_ROOT = BACKEND_DIR.parent.parent
    CONTRACT_DIR = REPO_ROOT / "contract"
    TOOLS_DIR = REPO_ROOT / "tools"
    ALEMBIC_DIR = BACKEND_DIR / "alembic"
    ALEMBIC_INI = BACKEND_DIR / "alembic.ini"
    FRONTEND_DIST = BACKEND_DIR.parent / "frontend" / "dist"


def _default_data_dir() -> Path:
    """داخل EXE: مجلد data بجانب الملف التنفيذي؛ وإن مكتوب عليه، LOCALAPPDATA."""
    if not IS_FROZEN:
        return BACKEND_DIR / "data"
    preferred = Path(sys.executable).resolve().parent / "data"
    try:
        preferred.mkdir(parents=True, exist_ok=True)
        with open(preferred / ".write_probe", "a", encoding="utf-8"):
            pass
        return preferred
    except Exception:
        fallback = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "AccTracker" / "data"
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


DATA_DIR = Path(os.environ.get("PROTRAK_DATA_DIR", str(_default_data_dir())))
DB_PATH = Path(os.environ.get("PROTRAK_DB", str(DATA_DIR / "protrack.db")))
PHOTOS_DIR = DATA_DIR / "photos"


def ensure_dirs():
    for d in (DATA_DIR, PHOTOS_DIR):
        d.mkdir(parents=True, exist_ok=True)


def ensure_tools_on_path():
    """يضيف مجلد tools/ إلى sys.path (لاستيراد الـvalidator المشترك)."""
    p = str(TOOLS_DIR)
    if p not in sys.path:
        sys.path.insert(0, p)


ensure_dirs()
