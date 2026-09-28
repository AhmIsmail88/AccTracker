#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build ProTrack sample visit packages for Phase 0 (stdlib-only).

الاستخدام:
    python tools/make_sample_package.py
"""
import hashlib
import json
import os
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ecdsa_min  # noqa: E402
import xlsx_min  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SAMPLES = os.path.join(ROOT, "contract", "samples")
KEY_PATH = os.path.join(SAMPLES, "dev_key.json")

CREATED_AT = "2026-09-28T10:52:00+03:00"
DEVICE_ID = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"

PKG_IDS = {
    "valid": "11111111-1111-4111-8111-111111111111",
    "unsigned": "22222222-2222-4222-8222-222222222222",
    "invalid_photo": "33333333-3333-4333-8333-333333333333",
    "hierarchy_conflict": "44444444-4444-4444-8444-444444444444",
}

KEY = {}


def load_or_create_key():
    if os.path.exists(KEY_PATH):
        with open(KEY_PATH, "r", encoding="utf-8") as f:
            d = json.load(f)
        if all(k in d for k in ("d", "x", "y")):
            return {"d": int(d["d"], 16), "x": int(d["x"], 16), "y": int(d["y"], 16)}
    key = ecdsa_min.generate_key()
    os.makedirs(SAMPLES, exist_ok=True)
    with open(KEY_PATH, "w", encoding="utf-8") as f:
        json.dump(
            {
                "note": "DEV KEY ONLY — ProTrack sample tooling",
                "d": format(key["d"], "x"),
                "x": format(key["x"], "x"),
                "y": format(key["y"], "x"),
            },
            f,
            indent=2,
        )
    return key


def _meta_rows(package_id):
    return [
        ["package_id", "schema_version", "created_at", "device_id", "device_public_key", "device_fingerprint"],
        [package_id, 1, CREATED_AT, DEVICE_ID, KEY["pub"], KEY["fp"]],
    ]


def _visit_rows():
    return [
        ["visit_id", "location_code", "visit_type", "started_at", "ended_at", "notes", "status"],
        ["VISIT-001", "LOC-001", "ROUTINE", "2026-09-28T09:40:00+03:00", "2026-09-28T10:45:00+03:00", "", "EXPORTED"],
    ]


def _equipment_rows(tamper=False):
    rows = [
        ["row_id", "visit_id", "kind", "tag", "model", "running_hours", "pressure_bar", "status", "note"],
        [1, "VISIT-001", "MAIN_PUMP", "01", "ABC-500", 2340, 5.8, "RUNNING", ""],
        [2, "VISIT-001", "MAIN_PUMP", "02", "ABC-500", 2410, 5.7, "RUNNING", ""],
        [3, "VISIT-001", "MAIN_PUMP", "03", "ABC-500", 2360, 0.0, "FAULT", "اهتزاز وضغط منخفض"],
        [4, "VISIT-001", "MAIN_PUMP", "04", "ABC-500", 2390, 5.8, "RUNNING", ""],
    ]
    if tamper:
        rows[1][5] = 9999
    return rows


def _checklist_rows():
    rows = [["visit_id", "item_code", "status", "note"]]
    for i in range(1, 13):
        rows.append(["VISIT-001", "CHK-%02d" % i, "MINOR" if i in (2, 5) else "OK", ""])
    return rows


def _locations_rows(extra=None):
    rows = [
        ["row_id", "code", "type", "parent_code", "name", "status", "updated_at"],
        [1, "PRJ-001", "PROJECT", "", "مشروع الرياض", "ACTIVE", "2026-09-20T08:00:00+03:00"],
        [2, "RGN-001", "REGION", "PRJ-001", "المنطقة الشرقية", "ACTIVE", "2026-09-20T08:01:00+03:00"],
        [3, "ZN-001", "ZONE", "RGN-001", "محطة الشمال", "ACTIVE", "2026-09-20T08:02:00+03:00"],
        [4, "ZN-002", "ZONE", "RGN-001", "محطة الجنوب", "ACTIVE", "2026-09-20T08:03:00+03:00"],
        [5, "LOC-001", "LOCATION", "ZN-001", "غرفة المضخات الرئيسية", "ACTIVE", "2026-09-20T08:04:00+03:00"],
        [6, "LOC-002", "LOCATION", "ZN-001", "غرفة الفلاتر", "ACTIVE", "2026-09-20T08:05:00+03:00"],
        [7, "LOC-003", "LOCATION", "ZN-002", "بئر رقم 3", "ACTIVE", "2026-09-20T08:06:00+03:00"],
    ]
    if extra:
        rows.extend(extra)
    return rows


def _conflict_extra_rows():
    ts = "2026-09-28T11:00:00+03:00"
    return [
        [8, "LOC-901", "LOCATION", "ZN-001", "غرفة الفلاتر", "ACTIVE", ts],
        [9, "LOC-002", "LOCATION", "ZN-001", "غرفة الفلاتر القديمة", "ACTIVE", ts],
    ]


def _photo_bytes(name):
    return (
        b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
        + ("ProTrack sample photo: %s" % name).encode("utf-8")
        + b"\xff\xd9"
    )


def _build(name, package_id, sign=True, drop_taken_at_for=None, locations_extra=None, tamper=False):
    photos = [
        ("IMG_001.jpg", _photo_bytes("IMG_001.jpg")),
        ("IMG_002.jpg", _photo_bytes("IMG_002.jpg")),
        ("IMG_003.jpg", _photo_bytes("IMG_003.jpg")),
    ]
    targets = [("EQUIPMENT", "MAIN_PUMP-03"), ("CHECKLIST", "CHK-02"), ("LOCATION", "LOC-001")]
    photo_meta = []
    for idx, (fname, data) in enumerate(photos):
        photo_meta.append(
            {
                "path": "photos/" + fname,
                "sha256": hashlib.sha256(data).hexdigest(),
                "taken_at": "2026-09-28T10:%02d:00+03:00" % (15 + 5 * idx),
                "lat": 24.7136,
                "lon": 46.6753,
                "accuracy_m": 8,
                "capture_sig": ecdsa_min.sign_b64(data, KEY["key"]),
            }
        )

    def photos_sheet():
        rows = [["row_id", "file", "target_type", "target_ref", "taken_at", "lat", "lon", "accuracy_m", "sha256", "capture_sig"]]
        for idx, pm in enumerate(photo_meta):
            ttype, tref = targets[idx]
            rows.append(
                [
                    idx + 1,
                    pm["path"].split("/", 1)[1],
                    ttype,
                    tref,
                    pm["taken_at"],
                    pm["lat"],
                    pm["lon"],
                    pm["accuracy_m"],
                    pm["sha256"],
                    pm["capture_sig"],
                ]
            )
        return rows

    def make_xlsx(tamper_eq=False):
        return xlsx_min.write_workbook_bytes(
            [
                ("_meta", _meta_rows(package_id)),
                ("visit", _visit_rows()),
                ("equipment", _equipment_rows(tamper_eq)),
                ("checklist", _checklist_rows()),
                ("locations", _locations_rows(locations_extra)),
                ("photos", photos_sheet()),
            ]
        )

    xlsx_original = make_xlsx()
    xlsx_for_zip = make_xlsx(tamper_eq=True) if tamper else xlsx_original

    files = [{"path": "visit.xlsx", "sha256": hashlib.sha256(xlsx_original).hexdigest()}] + [
        dict(pm) for pm in photo_meta
    ]
    manifest = {
        "package_id": package_id,
        "schema_version": 1,
        "created_at": CREATED_AT,
        "device": {"device_id": DEVICE_ID, "public_key": KEY["pub"], "fingerprint": KEY["fp"]},
        "files": files,
    }
    if drop_taken_at_for:
        for fm in manifest["files"]:
            if fm["path"] == "photos/" + drop_taken_at_for:
                fm.pop("taken_at", None)
    manifest_bytes = json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8")
    sig_b64 = ecdsa_min.sign_b64(manifest_bytes, KEY["key"]) if sign else None

    out_path = os.path.join(SAMPLES, name)
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("visit.xlsx", xlsx_for_zip)
        for fname, data in photos:
            z.writestr("photos/" + fname, data)
        z.writestr("manifest.json", manifest_bytes)
        if sign:
            z.writestr("manifest.sig", sig_b64.encode("ascii"))
    print("built %-32s %8d bytes" % (name, os.path.getsize(out_path)))


def main():
    os.makedirs(SAMPLES, exist_ok=True)
    key = load_or_create_key()
    KEY["key"] = key
    KEY["pub"] = ecdsa_min.public_key_spki_b64(key)
    KEY["fp"] = ecdsa_min.fingerprint(KEY["pub"])
    print("device fingerprint:", KEY["fp"])
    _build("valid_package.zip", PKG_IDS["valid"])
    _build("tampered_package.zip", PKG_IDS["valid"], tamper=True)
    _build("unsigned_package.zip", PKG_IDS["unsigned"], sign=False)
    _build("invalid_photo_package.zip", PKG_IDS["invalid_photo"], drop_taken_at_for="IMG_002.jpg")
    _build("hierarchy_conflict_package.zip", PKG_IDS["hierarchy_conflict"], locations_extra=_conflict_extra_rows())
    print("samples written to:", SAMPLES)
    return 0


if __name__ == "__main__":
    sys.exit(main())
