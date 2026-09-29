# -*- coding: utf-8 -*-
"""فحوص السحب التلقائي الدوري (بعميل مزيّف — بدون Firebase حقيقي)."""
import os
import time

from app.config import CONTRACT_DIR
from app.services import cloud_pull
from app.services.auto_pull import DEFAULT_INTERVAL, MIN_INTERVAL, manager


def _wait(predicate, timeout=5.0):
    end = time.time() + timeout
    while time.time() < end:
        if predicate():
            return True
        time.sleep(0.05)
    return predicate()

SAMPLES = os.path.join(str(CONTRACT_DIR), "samples")


def _read(name):
    with open(os.path.join(SAMPLES, name), "rb") as f:
        return f.read()


class FakeCloud:
    def __init__(self, packages):
        self._packages = packages

    def list_packages(self):
        return [
            cloud_pull.CloudPackage(file_name=n, blob_path="packages/dev/" + n)
            for n in self._packages
        ]

    def download(self, blob_path):
        return _read(blob_path.rsplit("/", 1)[-1])


def test_auto_defaults_disabled(client):
    body = client.get("/api/cloud/auto").json()
    assert body["enabled"] is False
    assert body["interval_seconds"] == DEFAULT_INTERVAL
    assert body["last_run_at"] is None


def test_auto_enable_persist_and_disable(client):
    r = client.post("/api/cloud/auto", json={"enabled": True, "interval_seconds": 120})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["enabled"] is True
    assert body["interval_seconds"] == 120

    # المهمة الخلفية بدأت فعلًا في الـevent loop (فحص anti-regression لتعارض الأسماء)
    assert _wait(lambda: manager._task is not None), "المهمة الخلفية لم تبدأ"

    # الاستمرارية: القراءة تعكس ما حُفظ
    again = client.get("/api/cloud/auto").json()
    assert again["enabled"] is True
    assert again["interval_seconds"] == 120

    # الحد الأدنى: 5 ثوانٍ تُرفع إلى 60
    r2 = client.post("/api/cloud/auto", json={"enabled": True, "interval_seconds": 5})
    assert r2.json()["interval_seconds"] == MIN_INTERVAL

    # الإيقاف
    r3 = client.post("/api/cloud/auto", json={"enabled": False})
    assert r3.json()["enabled"] is False
    assert _wait(lambda: manager._task is None), "المهمة الخلفية لم تتوقف"


def test_auto_run_once_imports(client, monkeypatch):
    fake = FakeCloud(["valid_package.zip"])
    monkeypatch.setattr(cloud_pull, "FirebaseCloudClient", lambda: fake)

    r = client.post("/api/cloud/auto/run")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["last_result"]["processed"] == 1
    assert body["last_result"]["results"][0]["status"] == "IMPORTED"
    assert body["last_error"] is None

    visits = client.get("/api/visits").json()
    assert len(visits) == 1

    # تكرار التشغيل: منع التكرار بفضل سجل cloud_import
    r2 = client.post("/api/cloud/auto/run")
    assert r2.json()["last_result"]["processed"] == 0


def test_auto_run_not_configured(client, monkeypatch):
    monkeypatch.delenv("FIREBASE_SERVICE_ACCOUNT", raising=False)
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
    monkeypatch.setattr(
        cloud_pull, "DEFAULT_SERVICE_ACCOUNT", cloud_pull.config.DATA_DIR / "no-such-file.json"
    )

    r = client.post("/api/cloud/auto/run")
    body = r.json()
    assert body["last_run_at"] is not None
    assert body["last_error"] is not None
    assert "غير مهيأ" in body["last_error"]
