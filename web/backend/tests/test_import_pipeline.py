# -*- coding: utf-8 -*-
"""فحوص خط الاستيراد: الحالات الستة الأساسية."""
import os

from app.config import CONTRACT_DIR

SAMPLES = os.path.join(str(CONTRACT_DIR), "samples")


def _upload(client, name):
    with open(os.path.join(SAMPLES, name), "rb") as f:
        return client.post("/api/imports", files={"file": (name, f, "application/zip")})


def test_import_valid_then_duplicate(client):
    r = _upload(client, "valid_package.zip")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "IMPORTED"
    assert body["validator_status"] == "PASS"
    assert body["counts"]["locations_created"] == 7
    assert body["counts"]["visit_created"] is True
    assert body["counts"]["equipment_new"] == 4

    r2 = _upload(client, "valid_package.zip")
    assert r2.json()["status"] == "DUPLICATE"

    tree = client.get("/api/locations/tree").json()
    assert tree[0]["code"] == "PRJ-001"
    assert tree[0]["review_status"] == "NEW_FROM_FIELD"
    locs = tree[0]["regions"][0]["zones"][0]["locations"]
    assert locs[0]["code"] == "LOC-001"

    rr = client.post("/api/locations/LOC-001/review")
    assert rr.json()["review_status"] == "OK"

    visits = client.get("/api/visits").json()
    assert visits[0]["visit_id"] == "VISIT-001"

    assets = client.get("/api/assets").json()
    assert len(assets) == 4
    pump1 = [a for a in assets if a["tag"] == "01"][0]
    assert pump1["running_hours"] == 2340
    assert pump1["asset_code"] == "LOC-001-MP-01"


def test_import_conflict_package(client):
    r = _upload(client, "hierarchy_conflict_package.zip")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "IMPORTED"
    assert body["counts"]["hierarchy_conflicts"] >= 2

    conflicts = client.get("/api/locations/conflicts").json()
    types = {c["type"] for c in conflicts}
    assert "DUPLICATE_NAME" in types
    assert "CODE_DATA_CONFLICT" in types


def test_import_tampered_rejected_without_side_effects(client):
    r = _upload(client, "tampered_package.zip")
    assert r.json()["status"] == "FAILED"
    assert client.get("/api/visits").json() == []
    assert client.get("/api/locations/tree").json() == []


def test_import_unsigned_rejected(client):
    r = _upload(client, "unsigned_package.zip")
    assert r.json()["status"] == "REJECTED"
