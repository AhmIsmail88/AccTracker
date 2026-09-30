# -*- coding: utf-8 -*-
"""فحوص طبيب السحابة (بعميل مزيّف — بدون شبكة حقيقية)."""


class FakeResp:
    def __init__(self, status_code, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def json(self):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload


class FakeClient:
    """عميل مزيّف: مسارات بحسب URL substring."""

    def __init__(self, routes):
        self.routes = routes
        self.calls = []

    def _f(self, url, **kw):
        self.calls.append(url)
        for frag, resp in self.routes.items():
            if frag in url:
                return resp
        return FakeResp(500, text="unrouted: %s" % url)

    def get(self, url, **kw):
        return self._f(url, **kw)

    def post(self, url, **kw):
        return self._f(url, **kw)


def _cfg(monkeypatch, project="protrack-b5818", bucket="protrack-b5818.firebasestorage.app", key="AIzaTEST"):
    from app.services import cloud_doctor

    monkeypatch.setattr(
        cloud_doctor, "load_client_config",
        lambda: {"path": "x", "project_id": project, "bucket": bucket, "api_key": key},
    )


def test_doctor_all_green(monkeypatch):
    from app.services import cloud_doctor

    _cfg(monkeypatch)
    fake = FakeClient({
        "identitytoolkit": FakeResp(200, {"idToken": "tok-1"}),
        "firestore.googleapis.com": FakeResp(403, {"error": {"message": "Missing or insufficient permissions."}}),
        "storage.googleapis.com": FakeResp(401, {"error": {"message": "denied"}}),
        "firebasestorage.googleapis.com": FakeResp(200, {"items": []}),
    })
    # ملاحظة: firestore مع توكن المفروض 200 — لكن مسار واحد لكل URL؛ نعالجها بعميل خاص
    class FakeClient2:
        def __init__(self):
            self.has_token = False

        def get(self, url, **kw):
            if "firebasestorage.googleapis.com" in url:
                return FakeResp(200, {"items": []})
            if "firestore.googleapis.com" in url:
                if kw.get("headers"):
                    return FakeResp(200, {"documents": []})
                return FakeResp(403, {"error": {"message": "denied"}})
            if "storage.googleapis.com" in url:
                return FakeResp(401, {"error": {"message": "denied"}})
            return FakeResp(500)

        def post(self, url, **kw):
            return FakeResp(200, {"idToken": "tok-1"})

    report = cloud_doctor.run_doctor(client=FakeClient2(), service_account=False)
    by_id = {c["id"]: c for c in report["checks"]}
    assert by_id["anonymous_auth"]["status"] == "ok"
    assert by_id["firestore_base"]["status"] == "ok"
    assert by_id["firestore_rules"]["status"] == "ok"
    assert by_id["storage_bucket"]["status"] == "ok"
    assert report["summary"]["device_ready"] is True
    assert report["summary"]["web_ready"] is False  # service account تم تخطيه


def test_doctor_anonymous_disabled(monkeypatch):
    from app.services import cloud_doctor

    _cfg(monkeypatch)

    class FakeC:
        def get(self, url, **kw):
            if "firestore.googleapis.com" in url:
                return FakeResp(403, {"error": {"message": "denied"}})
            if "storage.googleapis.com" in url:
                return FakeResp(401, {"error": {"message": "denied"}})
            return FakeResp(500)

        def post(self, url, **kw):
            return FakeResp(400, {"error": {"message": "ADMIN_ONLY_OPERATION"}})

    report = cloud_doctor.run_doctor(client=FakeC(), service_account=False)
    by_id = {c["id"]: c for c in report["checks"]}
    assert by_id["anonymous_auth"]["status"] == "fail"
    assert "Anonymous" in (by_id["anonymous_auth"]["hint"] or "")
    assert by_id["firestore_rules"]["status"] == "skip"
    assert report["summary"]["device_ready"] is False


def test_doctor_storage_missing(monkeypatch):
    from app.services import cloud_doctor

    _cfg(monkeypatch)

    class FakeC:
        def get(self, url, **kw):
            if "firestore.googleapis.com" in url:
                if kw.get("headers"):
                    return FakeResp(200, {"documents": []})
                return FakeResp(403, {"error": {"message": "denied"}})
            if "storage.googleapis.com" in url:
                return FakeResp(404, {"error": {"message": "The specified bucket does not exist."}})
            return FakeResp(500)

        def post(self, url, **kw):
            return FakeResp(200, {"idToken": "tok"})

    report = cloud_doctor.run_doctor(client=FakeC(), service_account=False)
    by_id = {c["id"]: c for c in report["checks"]}
    assert by_id["storage_bucket"]["status"] == "fail"
    assert "Get started" in (by_id["storage_bucket"]["hint"] or "")
    assert report["summary"]["device_ready"] is False


def test_doctor_no_config(monkeypatch):
    from app.services import cloud_doctor

    monkeypatch.setattr(cloud_doctor, "load_client_config", lambda: None)
    report = cloud_doctor.run_doctor(client=FakeClient({}), service_account=False)
    by_id = {c["id"]: c for c in report["checks"]}
    assert by_id["client_config"]["status"] == "fail"
    assert by_id["anonymous_auth"]["status"] == "skip"
    assert report["summary"]["all_ready"] is False
