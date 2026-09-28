# -*- coding: utf-8 -*-
"""خدمات شجرة المواقع: الشجرة، CRUD، دمج الحزم (قواعد §4.5)، والتعارضات."""
import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.db.models import HierarchyConflict, Location, Project, Region, Zone

TYPE_ORDER = {"PROJECT": 0, "REGION": 1, "ZONE": 2, "LOCATION": 3}
TYPE_CODE_PREFIX = {"PROJECT": "PRJ", "REGION": "RGN", "ZONE": "ZN", "LOCATION": "LOC"}
PARENT_TYPE = {"PROJECT": None, "REGION": "PROJECT", "ZONE": "REGION", "LOCATION": "ZONE"}
MODEL_BY_TYPE = {"PROJECT": Project, "REGION": Region, "ZONE": Zone, "LOCATION": Location}
PARENT_ATTR = {"REGION": "project_id", "ZONE": "region_id", "LOCATION": "zone_id"}


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _s(v):
    return "" if v is None else str(v).strip()


# ---------- قراءة ----------

def get_by_code(db: Session, code: str):
    code = _s(code)
    for typ, model in MODEL_BY_TYPE.items():
        obj = db.query(model).filter(model.code == code).first()
        if obj is not None:
            return typ, obj
    return None, None


def _children_of(db, parent_typ, parent_id, child_typ):
    if child_typ == "REGION":
        return db.query(Region).filter(Region.project_id == parent_id).all()
    if child_typ == "ZONE":
        return db.query(Zone).filter(Zone.region_id == parent_id).all()
    if child_typ == "LOCATION":
        return db.query(Location).filter(Location.zone_id == parent_id).all()
    return []


def _parent_code_of(db, typ, obj):
    if typ == "REGION" and getattr(obj, "project_id", None):
        p = db.get(Project, obj.project_id)
        return p.code if p else None
    if typ == "ZONE" and getattr(obj, "region_id", None):
        p = db.get(Region, obj.region_id)
        return p.code if p else None
    if typ == "LOCATION" and getattr(obj, "zone_id", None):
        p = db.get(Zone, obj.zone_id)
        return p.code if p else None
    return None


def build_tree(db: Session, include_inactive: bool = False):
    def keep(o):
        return include_inactive or o.status == "ACTIVE"

    projects = [p for p in db.query(Project).order_by(Project.code).all() if keep(p)]
    regions = [r for r in db.query(Region).order_by(Region.code).all() if keep(r)]
    zones = [z for z in db.query(Zone).order_by(Zone.code).all() if keep(z)]
    locs = [l for l in db.query(Location).order_by(Location.code).all() if keep(l)]

    rmap, zmap, lmap = {}, {}, {}
    for r in regions:
        rmap.setdefault(r.project_id, []).append(r)
    for z in zones:
        zmap.setdefault(z.region_id, []).append(z)
    for l in locs:
        lmap.setdefault(l.zone_id, []).append(l)

    tree = []
    for p in projects:
        pnode = {
            "code": p.code, "name": p.name, "type": "PROJECT", "status": p.status,
            "source": p.source, "review_status": p.review_status, "regions": [],
        }
        for r in rmap.get(p.id, []):
            rnode = {
                "code": r.code, "name": r.name, "type": "REGION", "status": r.status,
                "source": r.source, "review_status": r.review_status, "zones": [],
            }
            for z in zmap.get(r.id, []):
                znode = {
                    "code": z.code, "name": z.name, "type": "ZONE", "status": z.status,
                    "source": z.source, "review_status": z.review_status, "locations": [],
                }
                for l in lmap.get(z.id, []):
                    znode["locations"].append({
                        "code": l.code, "name": l.name, "type": "LOCATION", "status": l.status,
                        "source": l.source, "review_status": l.review_status,
                    })
                rnode["zones"].append(znode)
            pnode["regions"].append(rnode)
        tree.append(pnode)
    return tree


# ---------- كتابة ----------

def next_code(db: Session, typ: str) -> str:
    prefix = TYPE_CODE_PREFIX[typ] + "-"
    model = MODEL_BY_TYPE[typ]
    codes = [c for (c,) in db.query(model.code).filter(model.code.like(prefix + "%")).all()]
    nums = []
    for c in codes:
        try:
            nums.append(int(str(c).split("-", 1)[1]))
        except (ValueError, IndexError):
            continue
    n = (max(nums) + 1) if nums else 1
    return "%s%03d" % (prefix, n)


def create_node(db, typ, name, parent_code=None, code=None, status="ACTIVE",
                source="WEB", review_status="OK", allow_missing_parent=False):
    typ = _s(typ).upper()
    if typ not in TYPE_ORDER:
        raise ValueError("نوع غير معروف: %s" % typ)
    name = _s(name)
    if not name:
        raise ValueError("الاسم مطلوب")
    status = _s(status).upper() or "ACTIVE"
    if status not in ("ACTIVE", "INACTIVE"):
        raise ValueError("حالة غير صحيحة: %s" % status)
    code = _s(code) or next_code(db, typ)
    if get_by_code(db, code)[1] is not None:
        raise ValueError("الكود موجود بالفعل: %s" % code)

    parent_id = None
    expected_parent = PARENT_TYPE[typ]
    if expected_parent:
        if parent_code:
            ptyp, pobj = get_by_code(db, parent_code)
            if pobj is None:
                if not allow_missing_parent:
                    raise ValueError("الأب غير موجود: %s" % parent_code)
            elif ptyp != expected_parent:
                if not allow_missing_parent:
                    raise ValueError("الأب %s يجب أن يكون %s" % (parent_code, expected_parent))
            else:
                parent_id = pobj.id
        elif not allow_missing_parent:
            raise ValueError("%s يتطلب parent_code" % typ)
    elif parent_code:
        raise ValueError("PROJECT لا يقبل parent_code")

    model = MODEL_BY_TYPE[typ]
    kwargs = dict(code=code, name=name, status=status, source=source,
                  review_status=review_status, created_at=_now(), updated_at=_now())
    if parent_id is not None:
        kwargs[PARENT_ATTR[typ]] = parent_id
    obj = model(**kwargs)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def update_node(db, code, name=None, parent_code=None, status=None):
    typ, obj = get_by_code(db, code)
    if obj is None:
        raise ValueError("العنصر غير موجود: %s" % code)
    if name is not None:
        name = _s(name)
        if not name:
            raise ValueError("الاسم مطلوب")
        obj.name = name
    if status is not None:
        st = _s(status).upper()
        if st not in ("ACTIVE", "INACTIVE"):
            raise ValueError("حالة غير صحيحة: %s" % status)
        obj.status = st
    if parent_code is not None:
        expected = PARENT_TYPE[typ]
        if expected is None:
            raise ValueError("PROJECT ليس له أب")
        ptyp, pobj = get_by_code(db, parent_code)
        if pobj is None or ptyp != expected:
            raise ValueError("أب غير صالح: %s" % parent_code)
        setattr(obj, PARENT_ATTR[typ], pobj.id)
    obj.updated_at = _now()
    db.commit()
    db.refresh(obj)
    return obj


def mark_reviewed(db, code):
    typ, obj = get_by_code(db, code)
    if obj is None:
        raise ValueError("العنصر غير موجود: %s" % code)
    obj.review_status = "OK"
    obj.updated_at = _now()
    db.commit()
    db.refresh(obj)
    return obj


# ---------- التعارضات ----------

def add_conflict(db, conflict_type, entity_type, code, incoming, existing, source_package):
    row = HierarchyConflict(
        conflict_type=conflict_type,
        entity_type=entity_type,
        code=_s(code),
        incoming_value=json.dumps(incoming, ensure_ascii=False) if incoming is not None else None,
        existing_value=json.dumps(existing, ensure_ascii=False) if existing is not None else None,
        source_package=source_package,
        detected_at=_now(),
        status="OPEN",
    )
    db.add(row)
    return row


def list_conflicts(db, status="OPEN"):
    q = db.query(HierarchyConflict)
    st = _s(status).upper()
    if st and st != "ALL":
        q = q.filter(HierarchyConflict.status == st)
    out = []
    for c in q.order_by(HierarchyConflict.id).all():
        out.append({
            "id": c.id, "type": c.conflict_type, "entity_type": c.entity_type, "code": c.code,
            "incoming": json.loads(c.incoming_value) if c.incoming_value else None,
            "existing": json.loads(c.existing_value) if c.existing_value else None,
            "package": c.source_package, "detected_at": c.detected_at, "status": c.status,
        })
    return out


def resolve_conflict(db, conflict_id, action):
    action = _s(action).upper()
    if action not in ("RESOLVED", "IGNORED"):
        raise ValueError("إجراء غير صحيح: %s" % action)
    row = db.get(HierarchyConflict, conflict_id)
    if row is None:
        raise ValueError("التعارض غير موجود: %s" % conflict_id)
    row.status = action
    db.commit()
    db.refresh(row)
    return row


# ---------- الدمج من الحزم (قواعد §4.5) ----------

def merge_import_rows(db, rows, package_id, source="ANDROID"):
    """يطبق قواعد الدمج على صفوف شيت locations القادمة من حزمة زيارة."""
    created = skipped = 0
    conflicts = 0

    def sort_key(r):
        t = _s(r.get("type")).upper()
        return (TYPE_ORDER.get(t, 9), str(r.get("row_id") or ""))

    for r in sorted(rows, key=sort_key):
        code = _s(r.get("code"))
        typ = _s(r.get("type")).upper()
        name = _s(r.get("name"))
        parent_code = _s(r.get("parent_code")) or None
        status = _s(r.get("status")).upper() or "ACTIVE"
        if not code or typ not in TYPE_ORDER or not name:
            continue  # الـvalidator علّم عليها مسبقًا

        etyp, existing = get_by_code(db, code)
        if existing is None:
            parent_ok = None  # None = الأب غير مطلوب (PROJECT) أو غير محدد
            if parent_code:
                ptyp, pobj = get_by_code(db, parent_code)
                if pobj is None or PARENT_TYPE[typ] != ptyp:
                    add_conflict(db, "MISSING_PARENT", typ, code,
                                 {"parent_code": parent_code, "parent_type": ptyp,
                                  "expected_type": PARENT_TYPE[typ]},
                                 None, package_id)
                    conflicts += 1
                    parent_ok = False
                else:
                    parent_ok = True
                    for sib in _children_of(db, ptyp, pobj.id, typ):
                        if _s(sib.name) == name:
                            add_conflict(db, "DUPLICATE_NAME", typ, code,
                                         {"name": name, "parent_code": parent_code},
                                         {"code": sib.code, "name": sib.name}, package_id)
                            conflicts += 1
                            break
            try:
                create_node(
                    db, typ, name,
                    parent_code=(parent_code if parent_ok else None),
                    code=code, status=status, source=source,
                    review_status="NEW_FROM_FIELD",
                    allow_missing_parent=(parent_ok is False),
                )
                created += 1
            except ValueError as e:
                add_conflict(db, "MERGE_ERROR", typ, code, {"error": str(e)}, None, package_id)
                conflicts += 1
        else:
            existing_parent = _parent_code_of(db, etyp, existing)
            same = (etyp == typ and _s(existing.name) == name
                    and (_s(existing_parent) or None) == parent_code)
            if same:
                skipped += 1
            else:
                add_conflict(db, "CODE_DATA_CONFLICT", typ, code,
                             {"name": name, "parent_code": parent_code, "type": typ},
                             {"name": existing.name, "parent_code": existing_parent, "type": etyp},
                             package_id)
                conflicts += 1
    db.commit()
    return {"created": created, "skipped": skipped, "conflicts": conflicts}


# ---------- Seed ----------

def seed_rows(db, rows):
    """إدخال أولي (Seed): إنشاء ما هو غير موجود فقط — Idempotent."""
    created = skipped = 0

    def sort_key(r):
        return (TYPE_ORDER.get(_s(r.get("type")).upper(), 9), str(r.get("row_id") or ""))

    for r in sorted(rows, key=sort_key):
        code = _s(r.get("code"))
        typ = _s(r.get("type")).upper()
        name = _s(r.get("name"))
        parent_code = _s(r.get("parent_code")) or None
        if not code or typ not in TYPE_ORDER or not name:
            continue
        if get_by_code(db, code)[1] is not None:
            skipped += 1
            continue
        try:
            create_node(db, typ, name, parent_code=parent_code, code=code,
                        source="SEED", review_status="OK")
            created += 1
        except ValueError:
            skipped += 1
    return {"created": created, "skipped": skipped}
