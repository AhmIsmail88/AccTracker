# -*- coding: utf-8 -*-
"""فحوص API الزيارات + عرض ملفات الصور (بعينة الحزمة الصحيحة)."""
import os

from app.config import CONTRACT_DIR

SAMPLES = os.path.join(str(CONTRACT_DIR), "samples")


def _read_valid_package() -> bytes:
    with open(os.path.join(SAMPLES, "valid_package.zip"), "rb") as f:
        return f.read()


def test_visit_list_and_photo_file(client):
    r = client.post(
        "/api/imports",
        files={"file": ("valid_package.zip", _read_valid_package(), "application/zip")},
    )
    assert r.status_code == 200, r.text

    visits = client.get("/api/visits").json()
    assert len(visits) == 1
    vid = visits[0]["visit_id"]
    assert visits[0]["status"]

    detail = client.get("/api/visits/%s" % vid).json()
    assert len(detail["photos"]) == 3
    assert detail["photos"][0]["taken_at"] is not None
    assert detail["photos"][0]["lat"] is not None

    photo = detail["photos"][0]
    assert photo["url"] is not None

    file_resp = client.get(photo["url"])
    assert file_resp.status_code == 200, file_resp.text
    assert file_resp.headers["content-type"].startswith("image/")
    assert len(file_resp.content) > 0

    # صورة غير موجودة
    assert client.get("/api/visits/%s/photos/99999/file" % vid).status_code == 404


def test_photo_visit_mismatch_404(client):
    r = client.post(
        "/api/imports",
        files={"file": ("valid_package.zip", _read_valid_package(), "application/zip")},
    )
    assert r.status_code == 200, r.text
    vid = client.get("/api/visits").json()[0]["visit_id"]

    # زيارة غير موجودة
    assert client.get("/api/visits/VISIT-NOPE/photos/1/file").status_code == 404

    # photo_id من زيارة أخرى (بعد استيراد زيارة ثانية بحزمة معدلة؟) — هنا نتحقق فقط
    # أن photo_id غير التابع للزيارة يُرفض
    detail = client.get("/api/visits/%s" % vid).json()
    real_id = detail["photos"][0]["id"]
    assert client.get("/api/visits/VISIT-NOPE/photos/%d/file" % real_id).status_code == 404
