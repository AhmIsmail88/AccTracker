# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec — AccTracker Desktop EXE (لوحة المهندس)."""
import os

from PyInstaller.utils.hooks import collect_all, collect_submodules

SPEC_DIR = os.path.abspath(SPECPATH)  # web/backend
REPO_ROOT = os.path.abspath(os.path.join(SPEC_DIR, "..", ".."))

datas = [
    (os.path.join(REPO_ROOT, "web", "frontend", "dist"), "frontend_dist"),
    (os.path.join(REPO_ROOT, "tools"), "tools"),
    (os.path.join(REPO_ROOT, "contract"), "contract"),
    (os.path.join(SPEC_DIR, "alembic"), "alembic"),
    (os.path.join(SPEC_DIR, "alembic.ini"), "."),
]
binaries = []
hiddenimports = []


def _add_all(name):
    try:
        d, b, h = collect_all(name)
        datas.extend(d)
        binaries.extend(b)
        hiddenimports.extend(h)
    except Exception:
        pass


for pkg in ("uvicorn", "firebase_admin", "alembic", "fitz", "pymupdf"):
    _add_all(pkg)
    hiddenimports.extend(collect_submodules(pkg))

for pkg in (
    "google.cloud.firestore",
    "google.cloud.storage",
    "google.api_core",
    "google.auth",
    "google.oauth2",
    "google.protobuf",
    "grpc",
):
    _add_all(pkg)

a = Analysis(
    [os.path.join(SPEC_DIR, "run_desktop.py")],
    pathex=[SPEC_DIR],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "pytest", "matplotlib"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="AccTracker",
    debug=False,
    strip=False,
    upx=False,
    console=True,
    icon=os.path.join(SPEC_DIR, "assets", "acctracker.ico"),
)
