import { useCallback, useEffect, useState } from "react";
import { api, type VisitDetail, type VisitRow } from "../api";

const TYPE_LABEL: Record<string, string> = {
  ROUTINE: "دورية",
  REPAIR: "إصلاح",
  INSPECTION: "فحص",
  INSTALLATION: "تركيب",
  EMERGENCY: "طارئة",
};

const CHK_LABEL: Record<string, { label: string; cls: string }> = {
  OK: { label: "سليم", cls: "ok" },
  MINOR: { label: "ملاحظة", cls: "warn" },
  FAULT: { label: "عطل", cls: "err" },
};

const EQUIP_LABEL: Record<string, string> = {
  MAIN_PUMP: "مضخة رئيسية",
  SUBMERSIBLE_PUMP: "مضخة غاطسة",
  FILTER: "فلتر",
};

function visitTypeLabel(t: string): string {
  return TYPE_LABEL[t] ?? t;
}

function chkBadge(status: string) {
  const info = CHK_LABEL[status] ?? { label: status, cls: "muted" };
  return <span className={`badge ${info.cls}`}>{info.label}</span>;
}

export default function VisitsPage() {
  const [visits, setVisits] = useState<VisitRow[] | null>(null);
  const [detail, setDetail] = useState<VisitDetail | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      setVisits(await api<VisitRow[]>("/api/visits"));
    } catch (e) {
      setError(String((e as Error).message ?? e));
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const openVisit = async (visitId: string) => {
    setBusyId(visitId);
    setError(null);
    try {
      setDetail(await api<VisitDetail>(`/api/visits/${encodeURIComponent(visitId)}`));
    } catch (e) {
      setError(String((e as Error).message ?? e));
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div>
      <h2 className="page-title">الزيارات الميدانية</h2>
      <p className="page-desc">
        كل زيارة سجّلها الفني من التطبيق — عُدّاد المعدات والفحوص وصور التوثيق بالكامل بعد الاستيراد.
      </p>

      <div className="toolbar">
        <button className="btn" onClick={() => void load()}>
          تحديث
        </button>
      </div>

      {error && <div className="error-box">{error}</div>}

      {!visits && !error && <div className="loading">جارٍ التحميل…</div>}
      {visits && visits.length === 0 && (
        <div className="card">
          <div className="empty">لا توجد زيارات بعد — تظهر تلقائيًا أول ما تُستورد حزمة فني.</div>
        </div>
      )}

      {visits && visits.length > 0 && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>الزيارة</th>
                <th>الموقع</th>
                <th>النوع</th>
                <th>البداية</th>
                <th>الحالة</th>
                <th>الحزمة</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {visits.map((v) => (
                <tr key={v.visit_id}>
                  <td className="mono">{v.visit_id}</td>
                  <td className="mono">{v.location_code}</td>
                  <td>{visitTypeLabel(v.visit_type)}</td>
                  <td className="muted">{v.started_at}</td>
                  <td>
                    <span className="badge info">{v.status}</span>
                  </td>
                  <td className="muted">
                    <span className="mono">{v.package_id}</span>
                  </td>
                  <td>
                    <button
                      className="btn"
                      onClick={() => void openVisit(v.visit_id)}
                      disabled={busyId === v.visit_id}
                    >
                      {busyId === v.visit_id ? "…" : "تفاصيل"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {detail && (
        <div className="card" style={{ marginTop: 18 }}>
          <div className="detail-head">
            <h3 style={{ margin: 0 }}>تفاصيل الزيارة {detail.visit_id}</h3>
            <span className="badge info">{detail.status}</span>
            <span className="type-chip">{visitTypeLabel(detail.visit_type)}</span>
            <button className="btn" onClick={() => setDetail(null)}>
              إغلاق
            </button>
          </div>
          <div className="kv" style={{ marginBottom: 10 }}>
            <span className="k">الموقع:</span>
            <span className="mono">{detail.location_code}</span>
            <span className="k">البداية:</span>
            <span className="muted">{detail.started_at}</span>
            {detail.ended_at && (
              <>
                <span className="k">النهاية:</span>
                <span className="muted">{detail.ended_at}</span>
              </>
            )}
          </div>

          <h3>المعدات ({detail.equipment.length})</h3>
          {detail.equipment.length === 0 ? (
            <div className="empty" style={{ padding: "10px 0" }}>لا توجد معدات.</div>
          ) : (
            <div className="table-wrap" style={{ marginBottom: 14 }}>
              <table>
                <thead>
                  <tr>
                    <th>النوع</th>
                    <th>الكود</th>
                    <th>الموديل</th>
                    <th>ساعات التشغيل</th>
                    <th>الضغط</th>
                    <th>الحالة</th>
                  </tr>
                </thead>
                <tbody>
                  {detail.equipment.map((e, i) => (
                    <tr key={i}>
                      <td>{EQUIP_LABEL[e.kind] ?? e.kind}</td>
                      <td className="mono">{e.tag}</td>
                      <td>{e.model}</td>
                      <td>{e.running_hours ?? "—"}</td>
                      <td>{e.pressure_bar ?? "—"}</td>
                      <td>
                        <span className="badge info">{e.status}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <h3>الفحوص ({detail.checklist.length})</h3>
          {detail.checklist.length === 0 ? (
            <div className="empty" style={{ padding: "10px 0" }}>لا توجد فحوص.</div>
          ) : (
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 14 }}>
              {detail.checklist.map((c, i) => (
                <span key={i} className="chip-row">
                  <span className="mono">{c.item_code}</span> {chkBadge(c.status)}
                </span>
              ))}
            </div>
          )}

          <h3>صور التوثيق ({detail.photos.length})</h3>
          {detail.photos.length === 0 ? (
            <div className="empty" style={{ padding: "10px 0" }}>لا توجد صور.</div>
          ) : (
            <div className="visit-photos">
              {detail.photos.map((p) => (
                <div className="visit-photo" key={p.id}>
                  {p.url ? (
                    <a href={p.url} target="_blank" rel="noreferrer">
                      <img src={p.url} alt={p.target_type || "photo"} loading="lazy" />
                    </a>
                  ) : (
                    <div className="photo-missing">الملف غير متاح</div>
                  )}
                  <div className="cap">
                    <span>{p.target_type || "—"}</span>
                    {p.taken_at && <span>{p.taken_at}</span>}
                  </div>
                  {p.lat != null && p.lon != null && (
                    <div className="cap">
                      <span className="mono">
                        {p.lat.toFixed(5)}, {p.lon.toFixed(5)}
                      </span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
