#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ProTrack Visit Package Validator — Phase 0 (stdlib-only).

الاستخدام:
    python tools/validate_package.py <package.zip> [--seen-db seen.json] [--contract-dir contract]

يطبع النتيجة النهائية كقيمة واحدة: PASS / FAIL / REJECT / DUPLICATE / FLAG
(انظر contract/README.md لمعاني حالات الخروج).
"""
import argparse
import hashlib
import json
import os
import re
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ecdsa_min  # noqa: E402
import xlsx_min  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

EXIT_CODES = {"PASS": 0, "FAIL": 1, "REJECT": 2, "DUPLICATE": 3, "FLAG": 4}

SHEET_COLUMNS = {
    "_meta": ["package_id", "schema_version", "created_at", "device_id", "device_public_key", "device_fingerprint"],
    "visit": ["visit_id", "location_code", "visit_type", "started_at", "ended_at", "notes", "status"],
    "equipment": ["row_id", "visit_id", "kind", "tag", "model", "running_hours", "pressure_bar", "status", "note"],
    "checklist": ["visit_id", "item_code", "status", "note"],
    "locations": ["row_id", "code", "type", "parent_code", "name", "status", "updated_at"],
    "photos": ["row_id", "file", "target_type", "target_ref", "taken_at", "lat", "lon", "accuracy_m", "sha256", "capture_sig"],
}

TYPE_ORDER = {"PROJECT": None, "REGION": "PROJECT", "ZONE": "REGION", "LOCATION": "ZONE"}
TYPE_CODE_PREFIX = {"PROJECT": "PRJ", "REGION": "RGN", "ZONE": "ZN", "LOCATION": "LOC"}
CODE_RE = re.compile(r"^(PRJ|RGN|ZN|LOC)-[0-9]{3,}$")
UUID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
SHA_RE = re.compile(r"^[0-9a-f]{64}$")


def _s(v):
    return "" if v is None else str(v).strip()


def _sheet_dicts(rows):
    if not rows:
        return []
    headers = [_s(h) for h in rows[0]]
    out = []
    for r in rows[1:]:
        if not any(v is not None and str(v).strip() != "" for v in r):
            continue
        d = {}
        for i, h in enumerate(headers):
            if not h:
                continue
            d[h] = r[i] if i < len(r) else None
        out.append(d)
    return out


def _check_locations(rows, entry):
    flagged = False
    by_code = {}
    for r in rows:
        code = _s(r.get("code"))
        typ = _s(r.get("type")).upper()
        name = _s(r.get("name"))
        parent = _s(r.get("parent_code")) or None
        if not code or not typ or not name:
            entry("FLAG", "locations row missing code/type/name (row_id=%s)" % _s(r.get("row_id")))
            flagged = True
            continue
        if typ not in TYPE_ORDER:
            entry("FLAG", "locations unknown type: %s (code=%s)" % (typ, code))
            flagged = True
            continue
        if not CODE_RE.match(code) or not code.startswith(TYPE_CODE_PREFIX[typ] + "-"):
            entry("FLAG", "locations code/type mismatch: %s (%s)" % (code, typ))
            flagged = True
        if typ == "PROJECT":
            if parent:
                entry("FLAG", "PROJECT %s should not have parent_code (%s)" % (code, parent))
                flagged = True
        else:
            if not parent:
                entry("FLAG", "%s %s missing parent_code" % (typ, code))
                flagged = True
        if code in by_code:
            if by_code[code] != (name, parent, typ):
                entry("FLAG", "duplicate code with different data: %s" % code)
                flagged = True
            else:
                entry("WARN", "duplicate identical row for code %s" % code)
        else:
            by_code[code] = (name, parent, typ)

    names_under = {}
    for code, (name, parent, typ) in by_code.items():
        names_under.setdefault((parent, name), []).append(code)
    for (parent, name), codes in names_under.items():
        if len(codes) > 1:
            entry("FLAG", "possible duplicate name under same parent: '%s' (%s) -> %s" % (name, parent, ", ".join(codes)))
            flagged = True

    type_rank = {"PROJECT": 0, "REGION": 1, "ZONE": 2, "LOCATION": 3}
    for code, (name, parent, typ) in by_code.items():
        if parent and parent in by_code:
            parent_type = by_code[parent][2]
            # الأب لازم يكون أعلى في السلسلة — يسمح بتخطي مستويات ناقصة (زر/منطقة)
            if type_rank.get(parent_type, 99) >= type_rank.get(typ, -1):
                entry("FLAG", "parent type mismatch: %s(%s) parent %s(%s)" % (code, typ, parent, parent_type))
                flagged = True
    return flagged


def _check_equipment(rows, entry):
    flagged = False
    for r in rows:
        rid = _s(r.get("row_id"))
        for k in ("kind", "tag", "model"):
            if not _s(r.get(k)):
                entry("FLAG", "equipment row %s missing %s" % (rid, k))
                flagged = True
        for k in ("running_hours", "pressure_bar"):
            v = r.get(k)
            if v is None or _s(v) == "":
                entry("FLAG", "equipment row %s missing %s" % (rid, k))
                flagged = True
            else:
                try:
                    float(v)
                except (TypeError, ValueError):
                    entry("FLAG", "equipment row %s: %s not numeric (%r)" % (rid, k, v))
                    flagged = True
    return flagged


def _check_visit(rows, locations_rows, entry):
    flagged = False
    if not rows:
        entry("FLAG", "visit sheet has no data rows")
        return True
    r = rows[0]
    if not _s(r.get("visit_id")):
        entry("FLAG", "visit.visit_id missing")
        flagged = True
    lc = _s(r.get("location_code"))
    if not lc:
        entry("FLAG", "visit.location_code missing")
        flagged = True
    else:
        codes = {_s(x.get("code")) for x in locations_rows}
        if lc not in codes:
            entry("WARN", "visit.location_code %s not present in locations sheet" % lc)
    return flagged


def _check_checklist(rows, known_codes, entry):
    flagged = False
    for r in rows:
        code = _s(r.get("item_code"))
        if not code:
            entry("FLAG", "checklist row missing item_code")
            flagged = True
            continue
        if not _s(r.get("status")):
            entry("FLAG", "checklist %s missing status" % code)
            flagged = True
        if known_codes and code not in known_codes:
            entry("WARN", "checklist item_code %s not in checklist_items.json" % code)
    return flagged


def _check_photos_sheet(rows, package_names, entry):
    flagged = False
    for r in rows:
        f = _s(r.get("file"))
        if not f:
            entry("FLAG", "photos sheet row missing file")
            flagged = True
            continue
        if ("photos/" + f) not in package_names:
            entry("WARN", "photos sheet references %s not found in package" % f)
    return flagged


def _load_checklist_codes(contract_dir):
    if not contract_dir:
        contract_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "contract")
    path = os.path.join(contract_dir, "checklist_items.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {i.get("code") for i in data.get("items", [])}
    except Exception:
        return set()


def validate(package_path, seen_db_path=None, contract_dir=None):
    log = []

    def entry(level, msg):
        log.append((level, msg))

    fatal = False
    reject = False
    flagged = False
    package_id = None
    manifest = None
    manifest_bytes = None

    try:
        zf = zipfile.ZipFile(package_path)
        names = set(zf.namelist())
        entry("OK", "zip readable (%d entries)" % len(names))
    except Exception as e:
        return "FAIL", [("ERR", "cannot open zip: %s" % e)]

    with zf:
        required = ["visit.xlsx", "manifest.json"]
        missing = [n for n in required if n not in names]
        if missing:
            entry("ERR", "missing required entries: %s" % ", ".join(missing))
            fatal = True
        else:
            entry("OK", "required entries present (visit.xlsx, manifest.json)")

        has_sig = "manifest.sig" in names
        if not has_sig:
            entry("REJECT", "manifest.sig missing — unsigned package")
            reject = True

        if "manifest.json" in names:
            manifest_bytes = zf.read("manifest.json")
            try:
                manifest = json.loads(manifest_bytes.decode("utf-8"))
                entry("OK", "manifest.json parsed")
            except Exception as e:
                entry("ERR", "manifest.json not valid JSON: %s" % e)
                fatal = True

        dev = None
        if manifest is not None:
            for key in ("package_id", "schema_version", "created_at"):
                if key not in manifest:
                    entry("ERR", "manifest missing field: %s" % key)
                    fatal = True
            package_id = manifest.get("package_id")
            if not isinstance(package_id, str) or not UUID_RE.match(package_id or ""):
                entry("WARN", "package_id is not a UUID: %r" % (package_id,))
            else:
                entry("OK", "package_id: %s" % package_id)
            if manifest.get("schema_version") != 1:
                entry("WARN", "unexpected schema_version: %r" % manifest.get("schema_version"))
            dev = manifest.get("device")
            if not isinstance(dev, dict) or not all(k in dev for k in ("device_id", "public_key", "fingerprint")):
                entry("ERR", "manifest.device incomplete")
                fatal = True
                dev = None

            files = manifest.get("files")
            if not isinstance(files, list) or not files:
                entry("ERR", "manifest.files missing or empty")
                fatal = True
                files = []
            listed = set()
            ok_hashes = 0
            for f in files:
                path = f.get("path")
                sha = f.get("sha256")
                if not path or not sha:
                    entry("ERR", "files[] entry missing path/sha256: %r" % (f,))
                    fatal = True
                    continue
                listed.add(path)
                if not SHA_RE.match(str(sha).lower()):
                    entry("WARN", "files[] sha256 format odd for %s" % path)
                if path not in names:
                    if path.startswith("photos/"):
                        entry("FLAG", "photo listed in manifest but missing from package: %s" % path)
                        flagged = True
                    else:
                        entry("ERR", "file listed in manifest but missing from package: %s" % path)
                        fatal = True
                    continue
                real = hashlib.sha256(zf.read(path)).hexdigest()
                if real != str(sha).lower():
                    entry("ERR", "sha256 mismatch for %s (content modified?)" % path)
                    fatal = True
                else:
                    ok_hashes += 1
                if path.startswith("photos/"):
                    for reqk in ("taken_at", "lat", "lon", "accuracy_m", "capture_sig"):
                        if f.get(reqk) in (None, ""):
                            entry("FLAG", "photo metadata missing '%s' for %s" % (reqk, path))
                            flagged = True
            if ok_hashes:
                entry("OK", "file hashes match (%d files)" % ok_hashes)
            unlisted = sorted(n for n in names if n.startswith("photos/") and n not in listed)
            if unlisted:
                entry("WARN", "photo files present but not listed in manifest: %s" % ", ".join(unlisted))

        if has_sig and manifest_bytes is not None:
            pub = (dev or {}).get("public_key")
            if not pub:
                entry("ERR", "manifest.sig present but device.public_key unavailable")
                fatal = True
            else:
                try:
                    sig_b64 = zf.read("manifest.sig").decode("ascii", "replace").strip()
                    ok = ecdsa_min.verify_b64(pub, manifest_bytes, sig_b64)
                except Exception as e:
                    ok = False
                    entry("WARN", "signature check error: %s" % e)
                if ok:
                    entry("OK", "signature verified (ECDSA P-256)")
                else:
                    entry("ERR", "signature verification FAILED")
                    fatal = True

        wb = None
        if "visit.xlsx" in names:
            try:
                wb = xlsx_min.read_workbook(zf.read("visit.xlsx"))
                entry("OK", "visit.xlsx readable (%d sheets)" % len(wb))
            except Exception as e:
                entry("ERR", "cannot read visit.xlsx: %s" % e)
                fatal = True

        locations_rows = []
        if wb is not None:
            for sheet, cols in SHEET_COLUMNS.items():
                if sheet not in wb:
                    entry("ERR", "workbook missing sheet: %s" % sheet)
                    fatal = True
                    continue
                headers = [_s(h) for h in (wb[sheet][0] if wb[sheet] else [])]
                missing_cols = [c for c in cols if c not in headers]
                if missing_cols:
                    entry("ERR", "sheet %s missing columns: %s" % (sheet, ", ".join(missing_cols)))
                    fatal = True
                else:
                    entry("OK", "sheet %s columns OK" % sheet)

            locations_rows = _sheet_dicts(wb.get("locations", []))
            if _check_locations(locations_rows, entry):
                flagged = True
            if _check_equipment(_sheet_dicts(wb.get("equipment", [])), entry):
                flagged = True
            if _check_visit(_sheet_dicts(wb.get("visit", [])), locations_rows, entry):
                flagged = True
            known_codes = _load_checklist_codes(contract_dir)
            if _check_checklist(_sheet_dicts(wb.get("checklist", [])), known_codes, entry):
                flagged = True
            if _check_photos_sheet(_sheet_dicts(wb.get("photos", [])), names, entry):
                flagged = True

    if fatal:
        status = "FAIL"
    elif reject:
        status = "REJECT"
    else:
        seen_ids = []
        if seen_db_path and os.path.exists(seen_db_path):
            try:
                with open(seen_db_path, "r", encoding="utf-8") as f:
                    seen_ids = json.load(f).get("package_ids", [])
            except Exception:
                seen_ids = []
        if package_id and package_id in seen_ids:
            status = "DUPLICATE"
            entry("DUPLICATE", "package_id already imported: %s" % package_id)
        elif flagged:
            status = "FLAG"
        else:
            status = "PASS"
        if seen_db_path and package_id and status in ("PASS", "FLAG", "DUPLICATE"):
            if package_id not in seen_ids:
                seen_ids.append(package_id)
            try:
                d = os.path.dirname(seen_db_path)
                if d:
                    os.makedirs(d, exist_ok=True)
                with open(seen_db_path, "w", encoding="utf-8") as f:
                    json.dump({"package_ids": seen_ids}, f, indent=2)
            except Exception as e:
                entry("WARN", "could not update seen-db: %s" % e)

    return status, log


def main():
    ap = argparse.ArgumentParser(description="ProTrack Visit Package Validator (Phase 0)")
    ap.add_argument("package")
    ap.add_argument("--seen-db", default=None, help="ملف JSON لتتبع الحزم المستوردة (منع التكرار)")
    ap.add_argument("--contract-dir", default=None, help="مجلد contract (افتراضياً ../contract)")
    args = ap.parse_args()

    status, log = validate(args.package, args.seen_db, args.contract_dir)
    print("== ProTrack Package Validator ==")
    print("Package: %s" % os.path.basename(args.package))
    for level, msg in log:
        print("[%s] %s" % (level, msg))
    print("STATUS: %s" % status)
    sys.exit(EXIT_CODES[status])


if __name__ == "__main__":
    main()
