# -*- coding: utf-8 -*-
"""سحب الحزم من السحابة (Firebase) → نفس خط الاستيراد → سجل منع تكرار.

- يقرأ مستندات Firestore من مجموعة ``packages`` (التي يرفعها تطبيق الفني)
- ينزّل ملفات الحزم من Storage ويشغّل عليها نفس ``import_package`` (نفس التحقق والدمج)
- يسجّل كل حزمة معالجة في جدول ``cloud_import`` حتى لا تُعالج مرتين

في الفحوص يمكن تمرير عميل مزيّف (fake client) بدل Firebase الحقيقي.
"""
import json
import os
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app import config
from app.db.models import CloudImport
from app.services.importer import import_package

DEFAULT_LIMIT = 20
SERVICE_ACCOUNT_ENV = "FIREBASE_SERVICE_ACCOUNT"
DEFAULT_SERVICE_ACCOUNT = config.DATA_DIR / "firebase-service-account.json"


class CloudNotConfigured(RuntimeError):
    """لا يوجد ملف اعتماد Firebase (service account) بعد."""


def service_account_path():
    """أماكن البحث عن ملف الاعتماد: متغير بيئة → GOOGLE_APPLICATION_CREDENTIALS → ملف افتراضي."""
    for env_name in (SERVICE_ACCOUNT_ENV, "GOOGLE_APPLICATION_CREDENTIALS"):
        value = os.environ.get(env_name)
        if value:
            return value
    if DEFAULT_SERVICE_ACCOUNT.exists():
        return str(DEFAULT_SERVICE_ACCOUNT)
    return None


@dataclass
class CloudPackage:
    file_name: str
    blob_path: str
    data: dict = field(default_factory=dict)


class FirebaseCloudClient:
    """عميل حقيقي: Firestore (بيانات الحزم) + Storage (ملفات الحزم)."""

    def __init__(self):
        path = service_account_path()
        if not path:
            raise CloudNotConfigured(
                "ضع ملف service account في %s أو اضبط %s"
                % (DEFAULT_SERVICE_ACCOUNT, SERVICE_ACCOUNT_ENV),
            )
        import firebase_admin
        from firebase_admin import credentials

        if not firebase_admin._apps:
            credential = credentials.Certificate(path)
            self._app = firebase_admin.initialize_app(credential)
        else:
            self._app = firebase_admin.get_app()

    def list_packages(self):
        from firebase_admin import firestore

        fs = firestore.client()
        out = []
        for doc in fs.collection("packages").stream():
            data = doc.to_dict() or {}
            name = data.get("fileName") or doc.id
            device = data.get("deviceId") or ""
            out.append(
                CloudPackage(
                    file_name=name,
                    blob_path="packages/%s/%s" % (device, name),
                    data=data,
                ),
            )
        return out

    def download(self, blob_path: str) -> bytes:
        from firebase_admin import storage

        bucket = storage.bucket()
        return bucket.blob(blob_path).download_as_bytes()


def pull_from_cloud(db: Session, client=None, limit: int = DEFAULT_LIMIT) -> dict:
    """يسحب الحزم الجديدة من السحابة ويستوردها (Idempotent بفضل جدول cloud_import)."""
    if client is None:
        client = FirebaseCloudClient()

    processed = {row.file_name for row in db.query(CloudImport).all()}
    results = []

    for pkg in client.list_packages():
        if len(results) >= limit:
            break
        if pkg.file_name in processed:
            continue
        try:
            data = client.download(pkg.blob_path)
        except Exception as exc:  # noqa: BLE001
            results.append({"file": pkg.file_name, "status": "DOWNLOAD_FAILED", "detail": str(exc)})
            continue
        outcome = import_package(db, data, pkg.file_name)
        status = outcome.get("status", "FAILED")
        db.add(
            CloudImport(
                file_name=pkg.file_name,
                status=status,
                details_json=json.dumps(outcome, ensure_ascii=False),
            ),
        )
        db.commit()
        results.append({"file": pkg.file_name, "status": status})

    return {"checked": len(results), "processed": len(results), "results": results}
