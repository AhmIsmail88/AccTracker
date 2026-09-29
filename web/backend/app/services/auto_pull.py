# -*- coding: utf-8 -*-
"""السحب الدوري (أولًا بأول) — مدير مهمة خلفية يسحب حزم Firebase دوريًا.

- الإعدادات محفوظة في جدول ``app_setting``: cloud.auto.enabled / cloud.auto.interval
- تبدأ مع الخادم عبر lifespan وتُوقف عند الإغلاق
- كل دورة تستخدم نفس ``pull_from_cloud`` (نفس التحقق والدمج ومنع التكرار)
"""
import asyncio
import threading
from datetime import datetime, timezone

from sqlalchemy.exc import OperationalError

from app.db.base import SessionLocal
from app.db.models import AppSetting
from app.services.cloud_pull import CloudNotConfigured, pull_from_cloud, service_account_path

ENABLED_KEY = "cloud.auto.enabled"
INTERVAL_KEY = "cloud.auto.interval"
DEFAULT_INTERVAL = 300       # كل 5 دقائق
MIN_INTERVAL = 60            # دقيقة واحدة — أقصر فترة
MAX_INTERVAL = 3600          # ساعة — أطول فترة


def _now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _clamp_interval(value):
    try:
        value = int(value)
    except (TypeError, ValueError):
        value = DEFAULT_INTERVAL
    return max(MIN_INTERVAL, min(MAX_INTERVAL, value))


class AutoPullManager:
    """مدير السحب الدوري (singleton على مستوى الخادم)."""

    def __init__(self):
        self._loop = None
        self._task = None
        self._lock = threading.Lock()
        self.enabled = False
        self.interval_seconds = DEFAULT_INTERVAL
        self.last_run_at = None
        self.last_result = None
        self.last_error = None

    # ---------- الحالة ----------
    def status(self):
        return {
            "enabled": self.enabled,
            "interval_seconds": self.interval_seconds,
            "min_interval": MIN_INTERVAL,
            "max_interval": MAX_INTERVAL,
            "configured": service_account_path() is not None,
            "last_run_at": self.last_run_at,
            "last_result": self.last_result,
            "last_error": self.last_error,
        }

    # ---------- الإعدادات (جدول app_setting) ----------
    def _load_settings(self):
        try:
            with SessionLocal() as db:
                rows = {
                    r.key: r.value
                    for r in db.query(AppSetting)
                    .filter(AppSetting.key.in_([ENABLED_KEY, INTERVAL_KEY]))
                    .all()
                }
        except OperationalError:
            rows = {}  # الجدول غير موجود بعد (قبل الهجرات) — القيم الافتراضية
        enabled = rows.get(ENABLED_KEY) == "1"
        interval = _clamp_interval(rows.get(INTERVAL_KEY, str(DEFAULT_INTERVAL)))
        return enabled, interval

    def _save_settings(self):
        with SessionLocal() as db:
            for key, value in (
                (ENABLED_KEY, "1" if self.enabled else "0"),
                (INTERVAL_KEY, str(self.interval_seconds)),
            ):
                row = db.get(AppSetting, key)
                if row is None:
                    db.add(AppSetting(key=key, value=value))
                else:
                    row.value = value
            db.commit()

    # ---------- دورة الحياة ----------
    def bootstrap(self):
        """يُستدعى عند تشغيل الخادم (داخل الـevent loop): يقرأ الإعدادات ويبدأ المهمة لو مفعّلة."""
        self._loop = asyncio.get_running_loop()
        self._task = None
        self.enabled, self.interval_seconds = self._load_settings()
        self.last_run_at = None
        self.last_result = None
        self.last_error = None
        if self.enabled:
            self._ensure_task()

    def shutdown(self):
        self._cancel_task()
        self._loop = None

    def apply(self, enabled, interval_seconds=None):
        """تشغيل/إيقاف (أو تغيير الفترة) — يحفظ الإعداد ويدير المهمة الخلفية."""
        if interval_seconds is not None:
            self.interval_seconds = _clamp_interval(interval_seconds)
        self.enabled = bool(enabled)
        try:
            self._save_settings()
        except Exception:  # noqa: BLE001 — يستمر مفعّلًا للجلسة حتى لو فشل الحفظ
            pass
        if self.enabled:
            self._ensure_task()
        else:
            self._cancel_task()
        return self.status()

    # ---------- المهمة الخلفية ----------
    def _ensure_task(self):
        loop = self._loop
        if loop is None or loop.is_closed():
            return

        def _mk():
            if not self.enabled:
                return
            if self._task and not self._task.done():
                return
            self._task = loop.create_task(self._run_loop())

        try:
            running = asyncio.get_running_loop()
        except RuntimeError:
            running = None
        if running is loop:
            _mk()
        else:
            loop.call_soon_threadsafe(_mk)

    def _cancel_task(self):
        task = self._task
        self._task = None
        loop = self._loop
        if task and not task.done() and loop and loop.is_running():
            loop.call_soon_threadsafe(task.cancel)

    async def _run_loop(self):
        while self.enabled:
            try:
                await asyncio.sleep(self.interval_seconds)
            except asyncio.CancelledError:
                break
            if not self.enabled:
                break
            try:
                await asyncio.to_thread(self.run_once_sync)
            except asyncio.CancelledError:
                break
            except Exception:  # noqa: BLE001 — المهمة الخلفية لا تسقط
                pass

    # ---------- دورة سحب واحدة ----------
    def run_once_sync(self, client=None):
        """دورة سحب واحدة الآن — آمنة للاستدعاء من threadpool أو من المهمة الخلفية."""
        with self._lock:
            try:
                with SessionLocal() as db:
                    result = pull_from_cloud(db, client=client, limit=50)
                self.last_run_at = _now_iso()
                self.last_result = result
                self.last_error = None
            except CloudNotConfigured:
                self.last_run_at = _now_iso()
                self.last_error = "غير مهيأ: لا يوجد ملف اعتماد Firebase (service account)"
            except Exception as exc:  # noqa: BLE001
                self.last_run_at = _now_iso()
                self.last_error = str(exc)
            return self.status()


manager = AutoPullManager()
