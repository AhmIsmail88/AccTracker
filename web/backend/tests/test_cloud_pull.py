# -*- coding: utf-8 -*-
"""فحوص سحب الحزم من السحابة (بعميل مزيّف — بدون Firebase حقيقي)."""
import os

from app.config import CONTRACT_DIR
from app.services import cloud_pull

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


def test_cloud_status_endpoint(client):
    resp = client.get("/api/cloud/status")
    assert resp.status_code == 200
    body = resp.json()
    assert "configured" in body


def test_pull_imports_and_dedupes(client, monkeypatch):
    fake = FakeCloud(["valid_package.zip"])
    monkeypatch.setattr(cloud_pull, "FirebaseCloudClient", lambda: fake)

    r = client.post("/api/cloud/pull")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["processed"] == 1
    assert body["results"][0]["status"] == "IMPORTED"

    visits = client.get("/api/visits").json()
    assert len(visits) == 1
    assert visits[0]["visit_id"] == "VISIT-001"

    # إعادة السحب: لا يعيد المعالجة (سجل cloud_import)
    r2 = client.post("/api/cloud/pull")
    assert r2.json()["processed"] == 0
    assert len(client.get("/api/visits").json()) == 1


def test_pull_rejects_tampered(client, monkeypatch):
    fake = FakeCloud(["tampered_package.zip"])
    monkeypatch.setattr(cloud_pull, "FirebaseCloudClient", lambda: fake)

    r = client.post("/api/cloud/pull")
    body = r.json()
    assert body["results"][0]["status"] == "FAILED"
    assert client.get("/api/visits").json() == []
    assert client.get("/api/locations/tree").json() == []


def test_pull_unchanged_when_not_configured(client, monkeypatch):
    monkeypatch.delenv("FIREBASE_SERVICE_ACCOUNT", raising=False)
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
    monkeypatch.setattr(cloud_pull, "DEFAULT_SERVICE_ACCOUNT", cloud_pull.config.DATA_DIR / "no-such-file.json")

    r = client.post("/api/cloud/pull")
    assert r.status_code == 503
