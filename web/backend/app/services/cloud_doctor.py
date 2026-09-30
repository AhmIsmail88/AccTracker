# -*- coding: utf-8 -*-
"""طبيب السحابة — فحص شامل لجاهزية المزامنة مع Firebase (تشخيص حقيقي بلا آثار جانبية).

الفحوص (كل فحص مستقل — لا يوقف غيره):
1. client_config  — وجود google-services.json (project_id / bucket / api key)
2. anonymous_auth — الدخول المجهول (نفس ما يفعله جهاز الفني بالظبط)
3. firestore_base — مشروع Firestore موجود (رفض القراءة بدون مصادقة = سليم)
4. firestore_rules— قواعد packages تقبل القراءة للموثّقين (بتوكن مجهول)
5. storage_bucket — الـbucket متنشّط + قواعد Storage تقبل قراءة الموثّقين
6. service_account— ملف الاعتماد (service account) + سحب حقيقي بالـadmin SDK

النواتج قابلة للعرض في GET /api/cloud/doctor
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import httpx

from app import config

IDENTITY_SIGNUP_BASE = "https://identitytoolkit.googleapis.com/v1/accounts:signUp?key="
FIRESTORE_DOCS = "https://firestore.googleapis.com/v1/projects/{pid}/databases/(default)/documents/packages"
STORAGE_LIST = "https://firebasestorage.googleapis.com/v0/b/{bucket}/o"
GCS_META = "https://storage.googleapis.com/storage/v1/b/{bucket}"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _candidate_google_services():
    env = os.environ.get("PROTRAK_GOOGLE_SERVICES")
    paths = []
    if env:
        paths.append(Path(env))
    paths.append(Path(config.BUNDLE_DIR) / "google-services.json")
    paths.append(Path(config.DATA_DIR) / "google-services.json")
    paths.append(Path(config.REPO_ROOT) / "android" / "app" / "google-services.json")
    out = []
    seen = set()
    for p in paths:
        key = str(p).lower()
        if key not in seen:
            out.append(p)
            seen.add(key)
    return out


def load_client_config():
    """يقرأ google-services.json من أوائل المسارات المتاحة."""
    for p in _candidate_google_services():
        if not p.is_file():
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        proj = data.get("project_info") or {}
        api_key = None
        for c in data.get("client") or []:
            for k in c.get("api_key") or []:
                api_key = k.get("current_key")
                if api_key:
                    break
            if api_key:
                break
        return {
            "path": str(p),
            "project_id": proj.get("project_id"),
            "bucket": proj.get("storage_bucket"),
            "api_key": api_key,
        }
    return None


def _check(cid, title, status, detail, hint=None):
    return {"id": cid, "title": title, "status": status, "detail": detail, "hint": hint}


def _err_message(resp):
    try:
        return resp.json().get("error", {}).get("message") or ""
    except Exception:
        return (resp.text or "")[:120]


def run_doctor(client=None, service_account=None):
    """يشغّل كل الفحوص ويعيد تقريرًا.

    client: عميل httpx (أو شبيه) — للفحوص؛ None = عميل حقيقي
    service_account: None = كشف تلقائي؛ False = تخطٍّ؛ نص = مسار الملف
    """
    if client is None:
        client = httpx.Client(timeout=25, follow_redirects=True)

    checks = []
    token = None

    # 1) الإعداد
    cfg = load_client_config()
    if not cfg:
        checks.append(_check(
            "client_config", "إعداد العميل (google-services.json)", "fail",
            "لم يُعثر على google-services.json",
            "ضعه في مجلد data أو اضبط PROTRAK_GOOGLE_SERVICES",
        ))
        checks.append(_check("anonymous_auth", "الدخول المجهول (Anonymous)", "skip", "متوقف على الإعداد"))
        checks.append(_check("firestore_base", "Firestore — المشروع", "skip", "متوقف على الإعداد"))
        checks.append(_check("firestore_rules", "قواعد Firestore", "skip", "متوقف على الإعداد"))
        checks.append(_check("storage_bucket", "Storage — الـbucket والقواعد", "skip", "متوقف على الإعداد"))
    else:
        checks.append(_check(
            "client_config", "إعداد العميل (google-services.json)", "ok",
            "المشروع: %s | الـbucket: %s" % (cfg["project_id"], cfg["bucket"]),
        ))

        # 2) الدخول المجهول (نفس مسار جهاز الفني)
        pid = cfg.get("project_id") or ""
        api_key = cfg.get("api_key")
        if not api_key:
            checks.append(_check(
                "anonymous_auth", "الدخول المجهول (Anonymous)", "fail",
                "لا يوجد api key في الملف",
                "أعد تنزيل google-services.json من Firebase Console",
            ))
        else:
            try:
                resp = client.post(IDENTITY_SIGNUP_BASE + (api_key or ""), json={"returnSecureToken": True})
                if resp.status_code == 200:
                    token = resp.json().get("idToken")
                    checks.append(_check(
                        "anonymous_auth", "الدخول المجهول (Anonymous)", "ok",
                        "جهاز الفني يقدر يسجّل دخول ويرفع ✔",
                    ))
                else:
                    msg = _err_message(resp)
                    hint = None
                    if msg == "ADMIN_ONLY_OPERATION":
                        hint = "فعّل Anonymous: Authentication ← Sign-in method ← Add new provider ← Anonymous ← Enable"
                    checks.append(_check(
                        "anonymous_auth", "الدخول المجهول (Anonymous)", "fail",
                        "تعذّر الدخول المجهول: %s" % (msg or resp.status_code),
                        hint,
                    ))
            except Exception as exc:  # noqa: BLE001
                checks.append(_check(
                    "anonymous_auth", "الدخول المجهول (Anonymous)", "fail",
                    "خطأ اتصال: %s" % exc,
                ))

        # 3) Firestore موجود؟ (بدون مصادقة يجب أن تُرفض)
        try:
            resp = client.get(FIRESTORE_DOCS.format(pid=pid))
            if resp.status_code in (401, 403):
                checks.append(_check(
                    "firestore_base", "Firestore — المشروع", "ok",
                    "المشروع متنشّط والقراءة العامة مرفوضة (سليم)",
                ))
            elif resp.status_code == 200:
                checks.append(_check(
                    "firestore_base", "Firestore — المشروع", "warn",
                    "القراءة متاحة بدون مصادقة! راجع القواعد",
                    "انشر firebase/firestore.rules فورًا",
                ))
            elif resp.status_code == 404:
                checks.append(_check(
                    "firestore_base", "Firestore — المشروع", "fail",
                    "Firestore غير منشأ (404)",
                    "Firebase Console ← Firestore Database ← Create database",
                ))
            else:
                checks.append(_check(
                    "firestore_base", "Firestore — المشروع", "warn",
                    "رد غير متوقع: HTTP %s" % resp.status_code,
                ))
        except Exception as exc:  # noqa: BLE001
            checks.append(_check("firestore_base", "Firestore — المشروع", "fail", "خطأ اتصال: %s" % exc))

        # 4) قواعد Firestore للموثّقين (توكن مجهول)
        if not token:
            checks.append(_check("firestore_rules", "قواعد Firestore", "skip", "يحتاج نجاح الدخول المجهول أولًا"))
        else:
            try:
                resp = client.get(FIRESTORE_DOCS.format(pid=pid), headers={"Authorization": "Bearer %s" % token})
                if resp.status_code == 200:
                    checks.append(_check(
                        "firestore_rules", "قواعد Firestore", "ok",
                        "قواعد packages تعمل للموثّقين ✔",
                    ))
                elif resp.status_code in (401, 403):
                    checks.append(_check(
                        "firestore_rules", "قواعد Firestore", "fail",
                        "القراءة مرفوضة للموثّق — القواعد غير منشورة أو خاطئة",
                        "انشر: firebase deploy --only firestore:rules (أو الصقها في Console ← Firestore ← Rules)",
                    ))
                else:
                    checks.append(_check(
                        "firestore_rules", "قواعد Firestore", "warn",
                        "رد غير متوقع: HTTP %s" % resp.status_code,
                    ))
            except Exception as exc:  # noqa: BLE001
                checks.append(_check("firestore_rules", "قواعد Firestore", "fail", "خطأ اتصال: %s" % exc))

        # 5) Storage: وجود الـbucket + قواعد القراءة
        bucket = cfg.get("bucket") or ""
        try:
            meta = client.get(GCS_META.format(bucket=bucket))
            if meta.status_code == 404:
                checks.append(_check(
                    "storage_bucket", "Storage — الـbucket والقواعد", "fail",
                    "الـbucket غير موجود (%s)" % bucket,
                    "Firebase Console ← Storage ← Get started لإنشاء الـbucket",
                ))
            else:
                # يوجد الـbucket (401/403 = موجود بلا صلاحية عامة) — نفحص القواعد بالتوكن
                if not token:
                    checks.append(_check(
                        "storage_bucket", "Storage — الـbucket والقواعد", "warn",
                        "الـbucket موجود — لم يُفحص الشرط (يحتاج الدخول المجهول)",
                    ))
                else:
                    try:
                        lst = client.get(
                            STORAGE_LIST.format(bucket=bucket),
                            headers={"Authorization": "Bearer %s" % token},
                        )
                        if lst.status_code == 200:
                            checks.append(_check(
                                "storage_bucket", "Storage — الـbucket والقواعد", "ok",
                                "الـbucket متنشّط وقواعد الحزم تعمل ✔",
                            ))
                        elif lst.status_code in (401, 403):
                            checks.append(_check(
                                "storage_bucket", "Storage — الـbucket والقواعد", "fail",
                                "قواعد Storage ترفض الموثّق",
                                "انشر: firebase deploy --only storage (أو الصقها في Console ← Storage ← Rules)",
                            ))
                        elif lst.status_code == 404:
                            checks.append(_check(
                                "storage_bucket", "Storage — الـbucket والقواعد", "fail",
                                "Storage غير منشأ",
                                "Firebase Console ← Storage ← Get started",
                            ))
                        else:
                            checks.append(_check(
                                "storage_bucket", "Storage — الـbucket والقواعد", "warn",
                                "رد غير متوقع: HTTP %s" % lst.status_code,
                            ))
                    except Exception as exc:  # noqa: BLE001
                        checks.append(_check("storage_bucket", "Storage — الـbucket والقواعد", "fail", "خطأ اتصال: %s" % exc))
        except Exception as exc:  # noqa: BLE001
            checks.append(_check("storage_bucket", "Storage — الـbucket والقواعد", "fail", "خطأ اتصال: %s" % exc))

    # 6) حساب الخدمة (لسحب الويب)
    if service_account is False:
        checks.append(_check("service_account", "حساب الخدمة (سحب الويب)", "skip", "تم التخطي بطلب"))
    else:
        from app.services.cloud_pull import FirebaseCloudClient, service_account_path

        sa_path = service_account if isinstance(service_account, str) else service_account_path()
        if not sa_path:
            checks.append(_check(
                "service_account", "حساب الخدمة (سحب الويب)", "fail",
                "ملف الاعتماد غير موجود",
                "Firebase Console ← Project settings ← Service accounts ← Generate new private key ← احفظه في data/firebase-service-account.json",
            ))
        elif not Path(sa_path).is_file():
            checks.append(_check(
                "service_account", "حساب الخدمة (سحب الويب)", "fail",
                "الملف غير موجود: %s" % sa_path,
            ))
        else:
            try:
                fc = FirebaseCloudClient()
                packages = fc.list_packages()
                checks.append(_check(
                    "service_account", "حساب الخدمة (سحب الويب)", "ok",
                    "متصل ✔ — عدد الحزم على السحابة: %d" % len(packages),
                ))
            except Exception as exc:  # noqa: BLE001
                checks.append(_check(
                    "service_account", "حساب الخدمة (سحب الويب)", "fail",
                    "فشل الاتصال: %s" % exc,
                ))

    # الملخص
    by_id = {c["id"]: c for c in checks}
    device_ready = all(
        by_id.get(k, {}).get("status") == "ok"
        for k in ("anonymous_auth", "firestore_rules", "storage_bucket")
    )
    web_ready = by_id.get("service_account", {}).get("status") == "ok"
    return {
        "generated_at": _now(),
        "checks": checks,
        "summary": {
            "device_ready": device_ready,   # مسار جهاز الفني: رفع الحزم
            "web_ready": web_ready,         # مسار الويب: سحب الحزم
            "all_ready": device_ready and web_ready,
        },
    }
