import { useCallback, useEffect, useState } from "react";
import { api, type CloudAutoStatus, type CloudPullResult, type CloudStatus } from "../api";

const INTERVALS: { value: number; label: string }[] = [
  { value: 60, label: "كل دقيقة" },
  { value: 300, label: "كل 5 دقايق" },
  { value: 900, label: "كل ربع ساعة" },
  { value: 1800, label: "كل نص ساعة" },
];

function intervalLabel(seconds: number): string {
  return INTERVALS.find((i) => i.value === seconds)?.label ?? `كل ${seconds} ثانية`;
}

export default function CloudPage() {
  const [status, setStatus] = useState<CloudStatus | null>(null);
  const [auto, setAuto] = useState<CloudAutoStatus | null>(null);
  const [result, setResult] = useState<CloudPullResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadStatus = useCallback(async () => {
    try {
      setStatus(await api<CloudStatus>("/api/cloud/status"));
      setAuto(await api<CloudAutoStatus>("/api/cloud/auto"));
    } catch (e) {
      setError(String((e as Error).message ?? e));
    }
  }, []);

  useEffect(() => {
    void loadStatus();
    const t = window.setInterval(() => void loadStatus(), 20000);
    return () => window.clearInterval(t);
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

  const setAutoMode = async (enabled: boolean, interval_seconds?: number) => {
    setError(null);
    try {
      setAuto(
        await api<CloudAutoStatus>("/api/cloud/auto", {
          method: "POST",
          body: JSON.stringify({ enabled, interval_seconds }),
        }),
      );
    } catch (e) {
      setError(String((e as Error).message ?? e));
    }
  };

  const runAutoNow = async () => {
    setError(null);
    try {
      setAuto(await api<CloudAutoStatus>("/api/cloud/auto/run", { method: "POST" }));
    } catch (e) {
      setError(String((e as Error).message ?? e));
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
          <h3>سحب يدوي الآن</h3>
          <p className="muted" style={{ fontSize: 13, marginTop: 0 }}>
            يسحب كل الحزم التي لم تُعالَج بعد (بدون تكرار) ويستوردها مباشرة.
          </p>
          <button className="btn primary" onClick={() => void pull()} disabled={busy || !status?.configured}>
            {busy ? "جارٍ السحب…" : "اسحب الآن"}
          </button>
        </div>
      </div>

      <div className="card" style={{ marginTop: 16 }}>
        <h3>السحب التلقائي (أولًا بأول)</h3>
        {!auto ? (
          <div className="loading">جارٍ التحميل…</div>
        ) : (
          <>
            <div className="toolbar" style={{ marginBottom: 8 }}>
              <button
                className={auto.enabled ? "btn" : "btn primary"}
                onClick={() => void setAutoMode(!auto.enabled)}
              >
                {auto.enabled ? "إيقاف السحب التلقائي" : "تشغيل السحب التلقائي"}
              </button>
              <select
                value={auto.interval_seconds}
                onChange={(e) => void setAutoMode(auto.enabled, Number(e.target.value))}
                disabled={!auto.enabled}
                style={{ font: "inherit", padding: "9px 12px", borderRadius: 10, border: "1px solid var(--line)" }}
              >
                {INTERVALS.map((i) => (
                  <option key={i.value} value={i.value}>
                    {i.label}
                  </option>
                ))}
              </select>
              <button className="btn" onClick={() => void runAutoNow()} disabled={!auto.configured}>
                دورة سحب الآن
              </button>
            </div>
            <p className="muted" style={{ fontSize: 13, margin: 0 }}>
              {auto.enabled
                ? `مفعّل — يسحب تلقائيًا ${intervalLabel(auto.interval_seconds)} ويستورد الوارد أولًا بأول.`
                : "متوقف — الحزم تُسحب يدويًا فقط."}
            </p>
            {(auto.last_run_at || auto.last_error) && (
              <p className="muted" style={{ fontSize: 13, margin: "6px 0 0" }}>
                {auto.last_run_at && <>آخر دورة: {auto.last_run_at}</>}
                {auto.last_result && (
                  <>
                    {" "}
                    — فُحصت {auto.last_result.checked}، استُوردت {auto.last_result.processed}
                  </>
                )}
                {auto.last_error && <> — ⚠ {auto.last_error}</>}
              </p>
            )}
          </>
        )}
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
