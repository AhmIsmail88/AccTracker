# -*- coding: utf-8 -*-
"""فحوص المخزون وأوامر العمل (§20/§33 Phase 6)."""
import os

from app.config import CONTRACT_DIR

SAMPLES = os.path.join(str(CONTRACT_DIR), "samples")


def _import_sample(client):
    with open(os.path.join(SAMPLES, "valid_package.zip"), "rb") as f:
        data = f.read()
    r = client.post("/api/imports", files={"file": ("valid_package.zip", data, "application/zip")})
    assert r.status_code == 200, r.text


def _add_part(client, code="BRG-6205", name="رمان بلي 6205", **kw):
    payload = {"part_code": code, "name": name, "unit": "قطعة", "min_stock": 2, "unit_cost": 35.0}
    payload.update(kw)
    r = client.post("/api/stock/parts", json=payload)
    assert r.status_code == 200, r.text
    return r.json()


# ---------- المخزون ----------

def test_part_create_and_stock_flow(client):
    p = _add_part(client)
    assert p["stock"] == 0.0
    assert p["low_stock"] is True  # 0 ≤ min 2

    # تكرار الكود مرفوض
    r = client.post("/api/stock/parts", json={"part_code": "BRG-6205", "name": "x"})
    assert r.status_code == 422

    # استلام 10
    r = client.post("/api/stock/movements", json={
        "part_id": p["id"], "movement_type": "IN", "qty": 10, "reference": "PO-100",
    })
    assert r.status_code == 200, r.text
    assert r.json()["stock_after"] == 10.0

    parts = client.get("/api/stock/parts").json()
    assert parts[0]["stock"] == 10.0
    assert parts[0]["low_stock"] is False

    # صرف 4
    r = client.post("/api/stock/movements", json={
        "part_id": p["id"], "movement_type": "OUT", "qty": 4,
    })
    assert r.json()["stock_after"] == 6.0

    # صرف أكبر من الرصيد مرفوض
    r = client.post("/api/stock/movements", json={
        "part_id": p["id"], "movement_type": "OUT", "qty": 999,
    })
    assert r.status_code == 422

    # حركة بنوع غير صالح
    r = client.post("/api/stock/movements", json={
        "part_id": p["id"], "movement_type": "STEAL", "qty": 1,
    })
    assert r.status_code == 422

    # الحركات مسجلة
    moves = client.get("/api/stock/movements", params={"part_id": p["id"]}).json()
    assert len(moves) == 2


def test_purchase_suggestions(client):
    _add_part(client, code="SEAL-01", name="سيل ميكانيكي", min_stock=3)
    r = client.get("/api/stock/suggestions").json()
    assert len(r) == 1
    assert r[0]["part_code"] == "SEAL-01"
    assert r[0]["suggested_qty"] >= 1
    assert r[0]["est_cost"] is not None

    # استلام يكفي الحد → لا اقتراح
    pid = r[0]["part_id"]
    client.post("/api/stock/movements", json={"part_id": pid, "movement_type": "IN", "qty": 10})
    assert client.get("/api/stock/suggestions").json() == []


# ---------- أوامر العمل ----------

def test_work_order_full_flow(client):
    _import_sample(client)
    p = _add_part(client, code="BRG-6205", name="رمان بلي")
    client.post("/api/stock/movements", json={"part_id": p["id"], "movement_type": "IN", "qty": 20})

    # إنشاء أمر عمل مرتبط بأصل العينة (له عطل مسجّل)
    r = client.post("/api/work-orders", json={
        "title": "استبدال الختم الميكانيكي",
        "asset_code": "LOC-001-MP-03",
        "description": "ضغط صفر — عطل مسجّل",
        "priority": "HIGH",
        "source": "AI",
        "source_ref": "suggestion-1",
    })
    assert r.status_code == 200, r.text
    wo = r.json()
    assert wo["wo_number"].startswith("WO-")
    assert wo["status"] == "OPEN"
    assert wo["location_code"] == "LOC-001"  # موروث من الأصل

    # تخطيط قطعة
    r = client.post("/api/work-orders/%d/parts" % wo["id"], json={
        "part_id": p["id"], "planned_qty": 2, "unit_cost": 40.0,
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["parts_count"] == 1
    assert body["planned_cost"] == 80.0

    # إصدار قطعة → ينقص الرصيد + يتسجل حدث PART_REPLACEMENT
    r = client.post("/api/work-orders/%d/parts/%d/issue" % (wo["id"], p["id"]), json={"qty": 2})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["parts"][0]["issued_qty"] == 2.0
    assert body["parts_cost"] == 80.0

    parts = client.get("/api/stock/parts").json()
    assert parts[0]["stock"] == 18.0

    # إرجاع 1
    r = client.post("/api/work-orders/%d/parts/%d/return" % (wo["id"], p["id"]), json={"qty": 1})
    assert r.status_code == 200, r.text
    assert r.json()["parts"][0]["returned_qty"] == 1.0
    parts = client.get("/api/stock/parts").json()
    assert parts[0]["stock"] == 19.0

    # إرجاع أكبر من غير المرتجع مرفوض
    r = client.post("/api/work-orders/%d/parts/%d/return" % (wo["id"], p["id"]), json={"qty": 5})
    assert r.status_code == 422

    # إغلاق الأمر
    r = client.patch("/api/work-orders/%d" % wo["id"], json={"status": "DONE", "closing_note": "تم"})
    assert r.status_code == 200, r.text
    closed = r.json()
    assert closed["status"] == "DONE"
    assert closed["closed_at"] is not None

    # لا تعديل على أمر مغلق
    r = client.post("/api/work-orders/%d/parts" % wo["id"], json={"part_id": p["id"], "planned_qty": 5})
    assert r.status_code == 422
    r = client.post("/api/work-orders/%d/parts/%d/issue" % (wo["id"], p["id"]), json={"qty": 1})
    assert r.status_code == 422

    # الفلترة
    listed = client.get("/api/work-orders", params={"status": "DONE"}).json()
    assert len(listed) == 1
    assert client.get("/api/work-orders", params={"status": "OPEN"}).json() == []


def test_work_order_validation(client):
    # بدون عنوان
    r = client.post("/api/work-orders", json={"title": "  "})
    assert r.status_code == 422

    # أولوية غير صالحة
    r = client.post("/api/work-orders", json={"title": "t", "priority": "URGENT"})
    assert r.status_code == 422

    # أمر غير موجود
    assert client.get("/api/work-orders/999").status_code == 404

    # إصدار قطعة غير مخططة
    r = client.post("/api/work-orders", json={"title": "t2"})
    wo_id = r.json()["id"]
    assert client.post("/api/work-orders/%d/parts/999/issue" % wo_id, json={"qty": 1}).status_code == 404
