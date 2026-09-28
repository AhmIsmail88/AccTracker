# -*- coding: utf-8 -*-
"""استيراد حزم الزيارة: تحقق → دمج التقسيم → زيارة/معدات/صور (§4 و§4.5).

ملاحظة: التحقق يتم على بايتات الحزمة مباشرة (بدون ملفات مؤقتة إطلاقًا).
"""
import io
import json
import zipfile
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app import config
from app.db.models import (Equipment, EquipmentEvent, ImportedPackage, Visit,
                           VisitChecklist, VisitEquipment, VisitPhoto)
from app.services import locations as loc_service
from app.services.sheet import sheet_dicts

KIND_ABBREV = {"MAIN_PUMP": "MP", "SUBMERSIBLE_PUMP": "SP", "FILTER": "FL"}


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _s(v):
    return "" if v is None else str(v).strip()


def _float(v):
    v = _s(v)
    if not v:
        return None
    try:
        return float(v)
    except ValueError:
        return None


def _first_float(*vals):
    for v in vals:
        f = _float(v)
        if f is not None:
            return f
    return None


def _load_contract_modules():
    config.ensure_tools_on_path()
    import validate_package  # type: ignore
    import xlsx_min  # type: ignore
    return validate_package, xlsx_min


def _make_asset_code(db, location_code, kind, tag):
    ab = KIND_ABBREV.get(_s(kind).upper(), (_s(kind)[:2].upper() or "EQ"))
    base = "%s-%s-%s" % (location_code, ab, tag)
    code = base
    n = 2
    while db.query(Equipment).filter(Equipment.asset_code == code).first() is not None:
        code = "%s-%d" % (base, n)
        n += 1
    return code


def import_package(db: Session, file_bytes: bytes, filename: str = "package.zip"):
    validate_package, xlsx_min = _load_contract_modules()

    # 1) تحقق كامل (توقيع/هاشات/شيتات) بنفس أداة Phase 0 — على البايتات مباشرة
    status, log = validate_package.validate(io.BytesIO(file_bytes))
    if status in ("FAIL", "REJECT"):
        return {
            "status": "REJECTED" if status == "REJECT" else "FAILED",
            "validator_status": status,
            "details": ["%s: %s" % (lvl, msg) for lvl, msg in log],
        }

    zf = zipfile.ZipFile(io.BytesIO(file_bytes))
    try:
        manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
        package_id = _s(manifest.get("package_id"))
        if not package_id:
            return {"status": "FAILED", "validator_status": status,
                    "details": ["manifest.package_id missing"]}

        existing = (db.query(ImportedPackage)
                      .filter(ImportedPackage.package_id == package_id).first())
        if existing is not None:
            return {"status": "DUPLICATE", "validator_status": status,
                    "details": ["package_id already imported at %s" % existing.imported_at]}

        # 2) دمج شجرة المواقع (قواعد §4.5)
        workbook = xlsx_min.read_workbook(zf.read("visit.xlsx"))
        merge = loc_service.merge_import_rows(
            db, sheet_dicts(workbook.get("locations", [])), package_id)

        # 3) الزيارة
        visit_rows = sheet_dicts(workbook.get("visit", []))
        v = visit_rows[0] if visit_rows else {}
        visit_id = _s(v.get("visit_id"))
        visit = db.query(Visit).filter(Visit.visit_id == visit_id).first()
        visit_created = False
        if visit is None:
            visit = Visit(
                visit_id=visit_id,
                location_code=_s(v.get("location_code")),
                visit_type=_s(v.get("visit_type")),
                started_at=_s(v.get("started_at")),
                ended_at=_s(v.get("ended_at")),
                notes=_s(v.get("notes")),
                status=_s(v.get("status")) or "IMPORTED",
                package_id=package_id,
                imported_at=_now(),
            )
            db.add(visit)
            db.commit()
            db.refresh(visit)
            visit_created = True

        # 4) المعدات + المطابقة + أحداث الزيارة
        counts = {"equipment_new": 0, "equipment_matched": 0}
        for r in sheet_dicts(workbook.get("equipment", [])):
            kind = _s(r.get("kind")).upper()
            tag = _s(r.get("tag"))
            model = _s(r.get("model"))
            st = _s(r.get("status"))
            rh = _float(r.get("running_hours"))
            pb = _float(r.get("pressure_bar"))
            eq = (db.query(Equipment)
                    .filter(Equipment.location_code == visit.location_code,
                            Equipment.kind == kind,
                            Equipment.tag == tag)
                    .first())
            if eq is None:
                eq = Equipment(
                    asset_code=_make_asset_code(db, visit.location_code, kind, tag),
                    location_code=visit.location_code,
                    kind=kind,
                    tag=tag,
                    model=model or None,
                    status=st or "RUNNING",
                    running_hours=rh,
                    running_hours_at=visit.ended_at or visit.started_at,
                    notes=_s(r.get("note")) or None,
                    created_at=_now(),
                    updated_at=_now(),
                )
                db.add(eq)
                db.flush()
                counts["equipment_new"] += 1
            else:
                if rh is not None:
                    eq.running_hours = rh
                    eq.running_hours_at = visit.ended_at or visit.started_at
                if st:
                    eq.status = st
                if model:
                    eq.model = model
                eq.updated_at = _now()
                counts["equipment_matched"] += 1
            db.add(EquipmentEvent(
                equipment_id=eq.id,
                event_at=visit.ended_at or visit.started_at or _now(),
                event_type="VISIT",
                source=package_id,
                reference_id=visit.visit_id,
                description="زيارة %s" % visit.visit_id,
            ))
            db.add(VisitEquipment(
                visit_ref_id=visit.id, kind=kind, tag=tag, model=model or None,
                running_hours=rh, pressure_bar=pb, status=st or None,
                note=_s(r.get("note")) or None,
            ))

        # 5) بنود الفحص
        for r in sheet_dicts(workbook.get("checklist", [])):
            db.add(VisitChecklist(
                visit_ref_id=visit.id,
                item_code=_s(r.get("item_code")),
                status=_s(r.get("status")),
                note=_s(r.get("note")) or None,
            ))

        # 6) الصور (استخراج الملفات + سجلات)
        photo_meta = {}
        for f in manifest.get("files", []):
            p = _s(f.get("path"))
            if p.startswith("photos/"):
                photo_meta[p.split("/", 1)[1]] = f
        pdir = config.PHOTOS_DIR / package_id
        pdir.mkdir(parents=True, exist_ok=True)
        names = set(zf.namelist())
        for r in sheet_dicts(workbook.get("photos", [])):
            fname = _s(r.get("file"))
            arc = "photos/" + fname
            dest = None
            if fname and arc in names:
                dest = pdir / fname
                with open(dest, "wb") as fo:
                    fo.write(zf.read(arc))
            meta = photo_meta.get(fname, {})
            db.add(VisitPhoto(
                visit_ref_id=visit.id,
                target_type=_s(r.get("target_type")),
                target_ref=_s(r.get("target_ref")),
                file_path=str(dest) if dest else "",
                taken_at=_s(r.get("taken_at")) or _s(meta.get("taken_at")),
                lat=_first_float(r.get("lat"), meta.get("lat")),
                lon=_first_float(r.get("lon"), meta.get("lon")),
                accuracy_m=_first_float(r.get("accuracy_m"), meta.get("accuracy_m")),
                sha256=_s(r.get("sha256")) or _s(meta.get("sha256")),
                capture_sig=_s(r.get("capture_sig")) or _s(meta.get("capture_sig")),
            ))

        # 7) سجل الحزمة (منع التكرار + Import Inbox)
        counts["locations_created"] = merge["created"]
        counts["locations_skipped"] = merge["skipped"]
        counts["hierarchy_conflicts"] = merge["conflicts"]
        counts["visit_created"] = visit_created
        db.add(ImportedPackage(
            package_id=package_id,
            device_id=_s((manifest.get("device") or {}).get("device_id")),
            device_fingerprint=_s((manifest.get("device") or {}).get("fingerprint")),
            filename=filename,
            status=status,
            counts_json=json.dumps(counts, ensure_ascii=False),
            imported_at=_now(),
        ))
        db.commit()
        return {"status": "IMPORTED", "validator_status": status, "counts": counts}
    finally:
        zf.close()
