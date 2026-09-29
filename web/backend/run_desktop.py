# -*- coding: utf-8 -*-
"""AccTracker Desktop — مشغّل لوحة المهندس (يعمل من الريبو أو من EXE).

دبل-كليك على AccTracker.exe:
  1) يحدّث قاعدة البيانات (alembic upgrade head)
  2) يبدأ خادم FastAPI على منفذ شاغر (8000 فما فوق)
  3) يفتح المتصفح على اللوحة تلقائيًا
إيقاف التطبيق = إغلاق نافذة الكونسول.
"""
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path


def _bundle_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", str(Path(sys.executable).resolve().parent)))
    return Path(__file__).resolve().parent


def _pick_port(start: int = 8000, tries: int = 25) -> int:
    for port in range(start, start + tries):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError("لا يوجد منفذ شاغر في المدى 8000-8024")


def _run_migrations(bundle: Path) -> None:
    from alembic import command as alembic_command
    from alembic.config import Config as AlembicConfig

    ini = bundle / "alembic.ini"
    if not ini.is_file():
        print(f"⚠ ملف alembic.ini غير موجود عند: {ini}")
        raise SystemExit(1)
    cfg = AlembicConfig(str(ini))
    cfg.set_main_option("script_location", str(bundle / "alembic"))
    alembic_command.upgrade(cfg, "head")


def main() -> int:
    bundle = _bundle_dir()
    if str(bundle) not in sys.path:
        sys.path.insert(0, str(bundle))

    print("=" * 62)
    print("  AccTracker — لوحة المهندس (Desktop)")
    print("  Advanced Construction Co. — By Ahmed Ismail")
    print("=" * 62)

    from app import config as app_config  # noqa: F401  (ينشئ مجلدات البيانات)

    print("• تحديث قاعدة البيانات ...")
    _run_migrations(bundle)
    print(f"• مجلد البيانات: {app_config.DATA_DIR}")

    port = _pick_port(8000)
    url = f"http://127.0.0.1:{port}"

    def _open_browser():
        time.sleep(2.0)
        try:
            webbrowser.open(url)
        except Exception:
            pass

    threading.Thread(target=_open_browser, daemon=True).start()

    print(f"• الخادم يعمل الآن على: {url}")
    print("  إن لم يُفتح المتصفح تلقائيًا، افتح العنوان أعلاه يدويًا.")
    print("  لإيقاف التطبيق: أغلق هذه النافذة (أو Ctrl+C).")
    print("-" * 62)

    import uvicorn

    from app.main import app as fastapi_app

    uvicorn.run(fastapi_app, host="127.0.0.1", port=port, log_level="info", access_log=False)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception:
        import traceback

        traceback.print_exc()
        try:
            input("حدث خطأ — اضغط Enter للإغلاق...")
        except Exception:
            pass
        raise SystemExit(1)
