import { useCallback, useEffect, useState } from "react";
import { api, type AlertsResponse, type AlertRow } from "../api";

const SEV: Record<string, { label: string; cls: string }> = {
  CRITICAL: { label: "حرج", cls: "err" },
  WARNING: { label: "تحذير", cls: "warn" },
  INFO: { label: "معلومة", cls: "info" },
};

const TYPE_AR: Record<string, string> = {
  PM_OVERDUE: "صيانة متأخرة",
  PM_DUE: "صيانة مستحقة",
  PM_SOON: "صيانة قريبة",
  FAULT_ACTIVE: "عطل نشط",
  REPEATED_FAULT: "عطل متكرر",
  PRESSURE_ANOMALY: "شذوذ ضغط",
  RUNNING_HOURS_ANOMALY: "شذوذ عداد الساعات",
  CHECKLIST_FAULT: "بند فحص بحالة عطل",
  PHOTO_NO_GPS: "صور بدون موقع GPS",
};

function sevBadge(s: string) {
  const info = SEV[s] ?? { label: s, cls: "muted" };
  return <span className={`badge ${info.cls}`}>{info.label}</span>;
}

function refLabel(a: AlertRow): string {
  const r = a.ref || {};
  const parts: string[] = [];
  if (r.manual_id != null) parts.push(`Manual #${r.manual_id}`);
  if (r.page != null) parts.push(`ص ${r.page}`);
  if (r.section) parts.push(String(r.section));
  return parts.join(" · ");
}

type SevFilter = "ALL" | "CRITICAL" | "WARNING" | "INFO";

export default function AlertsPage() {
  const [data, setData] = useState<AlertsResponse | null>(null);
  const [filter, setFilter] = useState<SevFilter>("ALL");
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      setData(await api<AlertsResponse>("/api/alerts"));
    } catch (e) {
      setError(String((e as Error).message ?? e));
    }
  }, []);

  useEffect(() => {
    void load();
    const t = window.setInterval(() => void load(), 30000);
    return () => window.clearInterval(t);
  }, [load]);

  const alerts = data?.alerts ?? [];
  const shown = filter === "ALL" ? alerts : alerts.filter((a) => a.severity === filter);

  return (
    <div>
      <h2 className="page-title">التنبيهات — محرك حتمي (§22)</h2>
      <p className="page-desc">
        تنبيهات محسوبة مباشرة من البيانات (قواعد المانوال + القراءات + الفحوص + الصور) — بلا استنتاجات AI.
        تتحدث تلقائيًا كل 30 ثانية.
      </p>

      <div className="toolbar">
        <button className={`btn ${filter === "ALL" ? "primary" : ""}`} onClick={() => setFilter("ALL")}>
          الكل ({data?.total ?? 0})
        </button>
        <button className={`btn ${filter === "CRITICAL" ? "primary" : ""}`} onClick={() => setFilter("CRITICAL")}>
          حرج ({data?.counts?.CRITICAL ?? 0})
        </button>
        <button className={`btn ${filter === "WARNING" ? "primary" : ""}`} onClick={() => setFilter("WARNING")}>
          تحذير ({data?.counts?.WARNING ?? 0})
        </button>
        <button className={`btn ${filter === "INFO" ? "primary" : ""}`} onClick={() => setFilter("INFO")}>
          معلومة ({data?.counts?.INFO ?? 0})
        </button>
        <button className="btn" onClick={() => void load()}>
          تحديث
        </button>
      </div>

      {error && <div className="error-box">{error}</div>}
      {!data && !error && <div className="loading">جارٍ التحميل…</div>}

      {data && shown.length === 0 && (
        <div className="card">
          <div className="empty">
            {filter === "ALL" ? "لا توجد تنبيهات حاليًا 🎉" : "لا توجد تنبيهات بهذه الشدة."}
          </div>
        </div>
      )}

      {shown.length > 0 && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>الشدة</th>
                <th>النوع</th>
                <th>الأصل/الموقع</th>
                <th>التفاصيل</th>
                <th>المرجع</th>
                <th>التاريخ</th>
              </tr>
            </thead>
            <tbody>
              {shown.map((a) => (
                <tr key={a.key}>
                  <td>{sevBadge(a.severity)}</td>
                  <td>{TYPE_AR[a.type] ?? a.title}</td>
                  <td>
                    {a.asset_code && <div className="mono">{a.asset_code}</div>}
                    {a.location_code && <div className="muted mono" style={{ fontSize: 12 }}>{a.location_code}</div>}
                    {a.visit_id && <div className="muted" style={{ fontSize: 12 }}>{a.visit_id}</div>}
                  </td>
                  <td style={{ maxWidth: 320, fontSize: 13 }}>{a.detail || "—"}</td>
                  <td className="muted" style={{ fontSize: 12.5 }}>{refLabel(a) || "—"}</td>
                  <td className="muted" style={{ fontSize: 12 }}>{a.at || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
