import { useCallback, useEffect, useState } from "react";
import { api, type CloudPullResult, type CloudStatus } from "../api";

export default function CloudPage() {
  const [status, setStatus] = useState<CloudStatus | null>(null);
  const [result, setResult] = useState<CloudPullResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadStatus = useCallback(async () => {
    try {
      setStatus(await api<CloudStatus>("/api/cloud/status"));
    } catch (e) {
      setError(String((e as Error).message ?? e));
    }
  }, []);

  useEffect(() => {
    void loadStatus();
  }, [loadStatus]);

  const pull = async () => {
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      setResult(await api<CloudPullResult>("/api/cloud/pull", { method: "POST" }));
    } catch (e) {
      setError(String((e as Error).message ?? e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      <h2 className="page-title">المزامنة السحابية</h2>
      <p className="page-desc">
        الأجهزة الميدانية ترفع الحزم الموقّعة تلقائيًا إلى Firebase عند توفر الشبكة — ومن هنا يسحب الخادم الحزم
        الجديدة ويستوردها بنفس قواعد التحقق والدمج.
      </p>

      <div className="grid cols-2">
        <div className="card">
          <h3>حالة الاتصال بالسحابة</h3>
          {!status && !error && <div className="loading">جارٍ الفحص…</div>}
          {status && (
            <>
              {status.configured ? (
                <p>
                  <span className="badge ok">مُهيّأة</span>
                </p>
              ) : (
                <p>
                  <span className="badge warn">بانتظار الإعداد</span>
                </p>
              )}
              <p className="muted" style={{ fontSize: 13, lineHeight: 1.8 }}>
                {status.configured
                  ? "ملف الاعتماد موجود — جاهز للسحب."
                  : `لتفعيل السحب: نزّل ملف Service Account من Firebase Console (Project settings ← Service accounts ← Generate new private key) وضعه في: ${status.service_account_path ?? "مجلد بيانات الخادم"} ثم أعد تشغيل الخادم.`}
              </p>
            </>
          )}
        </div>

        <div className="card">
          <h3>سحب الحزم الجديدة</h3>
          <p className="muted" style={{ fontSize: 13, marginTop: 0 }}>
            يسحب كل الحزم التي لم تُعالَج بعد (بدون تكرار) ويستوردها مباشرة.
          </p>
          <button className="btn primary" onClick={() => void pull()} disabled={busy || !status?.configured}>
            {busy ? "جارٍ السحب…" : "اسحب الآن"}
          </button>
        </div>
      </div>

      {error && (
        <div className="error-box" style={{ marginTop: 16 }}>
          {error}
        </div>
      )}

      {result && (
        <div className="card" style={{ marginTop: 16 }}>
          <h3>نتيجة السحب</h3>
          <p className="muted" style={{ fontSize: 13 }}>
            تم فحص {result.checked} حزمة — عُولجت {result.processed}.
          </p>
          {result.results.length === 0 ? (
            <div className="empty">لا توجد حزم جديدة في السحابة.</div>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>الملف</th>
                    <th>النتيجة</th>
                  </tr>
                </thead>
                <tbody>
                  {result.results.map((r, i) => (
                    <tr key={i}>
                      <td className="mono">{r.file}</td>
                      <td>
                        {r.status === "IMPORTED" ? (
                          <span className="badge ok">مستوردة</span>
                        ) : r.status === "DUPLICATE" ? (
                          <span className="badge muted">مكررة</span>
                        ) : (
                          <span className="badge err">{r.status}</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
