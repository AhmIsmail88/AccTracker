# -*- coding: utf-8 -*-
"""نماذج قاعدة البيانات — Phase 1.

وفق ARCHITECTURE.md §18/§19:
- التقسيم الإداري: project / region / zone / location (+ تعارضات الشجرة).
- المعدات وأحداثها.
- الزيارات المستوردة من الحزم (visit / visit_equipment / visit_checklist / visit_photo).
- سجل الحزم المستوردة (imported_package) لمنع التكرار.
"""
from datetime import datetime, timezone

from sqlalchemy import Column, Float, ForeignKey, Integer, String, Text

from app.db.base import Base


def utcnow_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Project(Base):
    __tablename__ = "project"

    id = Column(Integer, primary_key=True)
    code = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    status = Column(String, nullable=False, default="ACTIVE")        # ACTIVE / INACTIVE
    source = Column(String, nullable=False, default="WEB")           # WEB / ANDROID / SEED
    review_status = Column(String, nullable=False, default="OK")     # OK / NEW_FROM_FIELD
    created_at = Column(String, nullable=False, default=utcnow_iso)
    updated_at = Column(String, nullable=False, default=utcnow_iso)


class Region(Base):
    __tablename__ = "region"

    id = Column(Integer, primary_key=True)
    code = Column(String, unique=True, nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("project.id"), nullable=True)
    name = Column(String, nullable=False)
    status = Column(String, nullable=False, default="ACTIVE")
    source = Column(String, nullable=False, default="WEB")
    review_status = Column(String, nullable=False, default="OK")
    created_at = Column(String, nullable=False, default=utcnow_iso)
    updated_at = Column(String, nullable=False, default=utcnow_iso)


class Zone(Base):
    __tablename__ = "zone"

    id = Column(Integer, primary_key=True)
    code = Column(String, unique=True, nullable=False, index=True)
    region_id = Column(Integer, ForeignKey("region.id"), nullable=True)
    name = Column(String, nullable=False)
    status = Column(String, nullable=False, default="ACTIVE")
    source = Column(String, nullable=False, default="WEB")
    review_status = Column(String, nullable=False, default="OK")
    created_at = Column(String, nullable=False, default=utcnow_iso)
    updated_at = Column(String, nullable=False, default=utcnow_iso)


class Location(Base):
    __tablename__ = "location"

    id = Column(Integer, primary_key=True)
    code = Column(String, unique=True, nullable=False, index=True)
    zone_id = Column(Integer, ForeignKey("zone.id"), nullable=True)
    name = Column(String, nullable=False)
    status = Column(String, nullable=False, default="ACTIVE")
    source = Column(String, nullable=False, default="WEB")
    review_status = Column(String, nullable=False, default="OK")
    created_at = Column(String, nullable=False, default=utcnow_iso)
    updated_at = Column(String, nullable=False, default=utcnow_iso)


class HierarchyConflict(Base):
    __tablename__ = "hierarchy_conflict"

    id = Column(Integer, primary_key=True)
    conflict_type = Column(String, nullable=False)   # CODE_DATA_CONFLICT / DUPLICATE_NAME / MISSING_PARENT / MERGE_ERROR
    entity_type = Column(String, nullable=False)     # PROJECT / REGION / ZONE / LOCATION
    code = Column(String, nullable=False)
    incoming_value = Column(Text, nullable=True)     # JSON نصي
    existing_value = Column(Text, nullable=True)     # JSON نصي
    source_package = Column(String, nullable=True)
    detected_at = Column(String, nullable=False, default=utcnow_iso)
    status = Column(String, nullable=False, default="OPEN")  # OPEN / RESOLVED / IGNORED


class Equipment(Base):
    __tablename__ = "equipment"

    id = Column(Integer, primary_key=True)
    asset_code = Column(String, unique=True, nullable=False, index=True)
    location_code = Column(String, ForeignKey("location.code"), nullable=False)
    kind = Column(String, nullable=False)
    tag = Column(String, nullable=False, default="")
    name = Column(String, nullable=True)
    manufacturer = Column(String, nullable=True)
    model = Column(String, nullable=True)
    serial_no = Column(String, nullable=True)
    power_kw = Column(Float, nullable=True)
    flow_m3h = Column(Float, nullable=True)
    head_bar = Column(Float, nullable=True)
    voltage = Column(Float, nullable=True)
    installed_on = Column(String, nullable=True)
    warranty_until = Column(String, nullable=True)
    status = Column(String, nullable=False, default="RUNNING")
    running_hours = Column(Float, nullable=True)
    running_hours_at = Column(String, nullable=True)
    manual_id = Column(Integer, nullable=True)  # يُربط بالـManuals في Phase 3
    notes = Column(Text, nullable=True)
    created_at = Column(String, nullable=False, default=utcnow_iso)
    updated_at = Column(String, nullable=False, default=utcnow_iso)


class EquipmentEvent(Base):
    __tablename__ = "equipment_event"

    id = Column(Integer, primary_key=True)
    equipment_id = Column(Integer, ForeignKey("equipment.id"), nullable=False)
    event_at = Column(String, nullable=False)
    event_type = Column(String, nullable=False)      # VISIT / FAULT / PM / ...
    source = Column(String, nullable=True)
    reference_id = Column(String, nullable=True)
    description = Column(Text, nullable=True)


class Visit(Base):
    __tablename__ = "visit"

    id = Column(Integer, primary_key=True)
    visit_id = Column(String, unique=True, nullable=False, index=True)
    location_code = Column(String, nullable=False)
    visit_type = Column(String, nullable=True)
    started_at = Column(String, nullable=True)
    ended_at = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    status = Column(String, nullable=True)
    package_id = Column(String, nullable=True)
    imported_at = Column(String, nullable=True)


class VisitEquipment(Base):
    __tablename__ = "visit_equipment"

    id = Column(Integer, primary_key=True)
    visit_ref_id = Column(Integer, ForeignKey("visit.id"), nullable=False)
    kind = Column(String, nullable=True)
    tag = Column(String, nullable=True)
    model = Column(String, nullable=True)
    running_hours = Column(Float, nullable=True)
    pressure_bar = Column(Float, nullable=True)
    status = Column(String, nullable=True)
    note = Column(Text, nullable=True)


class VisitChecklist(Base):
    __tablename__ = "visit_checklist"

    id = Column(Integer, primary_key=True)
    visit_ref_id = Column(Integer, ForeignKey("visit.id"), nullable=False)
    item_code = Column(String, nullable=True)
    status = Column(String, nullable=True)
    note = Column(Text, nullable=True)


class VisitPhoto(Base):
    __tablename__ = "visit_photo"

    id = Column(Integer, primary_key=True)
    visit_ref_id = Column(Integer, ForeignKey("visit.id"), nullable=False)
    target_type = Column(String, nullable=True)
    target_ref = Column(String, nullable=True)
    file_path = Column(String, nullable=True)
    taken_at = Column(String, nullable=True)
    lat = Column(Float, nullable=True)
    lon = Column(Float, nullable=True)
    accuracy_m = Column(Float, nullable=True)
    sha256 = Column(String, nullable=True)
    capture_sig = Column(String, nullable=True)


class ImportedPackage(Base):
    __tablename__ = "imported_package"

    id = Column(Integer, primary_key=True)
    package_id = Column(String, unique=True, nullable=False, index=True)
    device_id = Column(String, nullable=True)
    device_fingerprint = Column(String, nullable=True)
    filename = Column(String, nullable=True)
    status = Column(String, nullable=True)          # PASS / FLAG
    counts_json = Column(Text, nullable=True)
    imported_at = Column(String, nullable=False, default=utcnow_iso)


# ============ Phase 3 — الـManuals (§6 / §18) ============

class Manual(Base):
    __tablename__ = "manual"

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    manufacturer = Column(String, nullable=True)
    model = Column(String, nullable=True)
    equipment_kind = Column(String, nullable=True)
    revision = Column(String, nullable=True)
    file_path = Column(String, nullable=False)
    sha256 = Column(String, unique=True, nullable=True)
    uploaded_at = Column(String, nullable=True)
    status = Column(String, nullable=False, default="READY")


class ManualSection(Base):
    __tablename__ = "manual_section"

    id = Column(Integer, primary_key=True)
    manual_id = Column(Integer, ForeignKey("manual.id"), nullable=False)
    page_start = Column(Integer, nullable=True)
    page_end = Column(Integer, nullable=True)
    section_title = Column(String, nullable=True)
    text = Column(Text, nullable=False)


class ManualChunk(Base):
    __tablename__ = "manual_chunk"

    id = Column(Integer, primary_key=True)
    manual_id = Column(Integer, ForeignKey("manual.id"), nullable=False)
    page = Column(Integer, nullable=True)
    section_title = Column(String, nullable=True)
    chunk_index = Column(Integer, nullable=True)
    text = Column(Text, nullable=False)
    embedding_ref = Column(Text, nullable=True)


class MaintenanceRule(Base):
    __tablename__ = "maintenance_rule"

    id = Column(Integer, primary_key=True)
    manual_id = Column(Integer, ForeignKey("manual.id"), nullable=True)
    equipment_kind = Column(String, nullable=True)
    model = Column(String, nullable=True)
    maintenance_type = Column(String, nullable=True)
    interval_hours = Column(Float, nullable=True)
    interval_days = Column(Integer, nullable=True)
    threshold_value = Column(Float, nullable=True)
    threshold_unit = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    source_page = Column(Integer, nullable=True)
    source_section = Column(String, nullable=True)
    confidence = Column(String, nullable=True)
    status = Column(String, nullable=False, default="DRAFT")


# ============ Phase Cloud — سجل سحب الحزم من السحابة ============

class CloudImport(Base):
    __tablename__ = "cloud_import"

    id = Column(Integer, primary_key=True)
    file_name = Column(String, unique=True, nullable=False, index=True)
    status = Column(String, nullable=False)
    details_json = Column(Text, nullable=True)
    pulled_at = Column(String, nullable=False, default=utcnow_iso)


# ============ إعدادات التطبيق (مفتاح/قيمة) ============

class AppSetting(Base):
    __tablename__ = "app_setting"

    key = Column(String, primary_key=True)
    value = Column(String, nullable=False)
    updated_at = Column(String, nullable=False, default=utcnow_iso)
