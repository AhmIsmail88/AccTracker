# -*- coding: utf-8 -*-


def test_locations_crud_and_tree(client):
    r = client.post("/api/locations", json={"type": "PROJECT", "name": "مشروع تجريبي"})
    assert r.status_code == 200, r.text
    code = r.json()["code"]
    assert code == "PRJ-001"

    r2 = client.post("/api/locations", json={"type": "REGION", "name": "منطقة أولى", "parent_code": code})
    assert r2.status_code == 200, r2.text

    r3 = client.post("/api/locations", json={"type": "REGION", "name": "خطأ", "parent_code": "PRJ-999"})
    assert r3.status_code == 422

    r4 = client.patch("/api/locations/" + code, json={"name": "مشروع معدّل"})
    assert r4.status_code == 200
    assert r4.json()["name"] == "مشروع معدّل"

    r5 = client.patch("/api/locations/" + code, json={"status": "INACTIVE"})
    assert r5.json()["status"] == "INACTIVE"

    assert client.get("/api/locations/tree").json() == []
    tree = client.get("/api/locations/tree?include_inactive=true").json()
    assert tree[0]["code"] == code
    assert tree[0]["regions"][0]["name"] == "منطقة أولى"
