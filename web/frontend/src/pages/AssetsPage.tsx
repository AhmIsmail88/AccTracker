import { useCallback, useEffect, useState } from "react";
import { api, type AssetDetail, type AssetRow } from "../api";

const HEALTH: Record<string, { label: string; cls: string }> = {
  NORMAL: { label: "سليمة", cls: "ok" },
  MAINTENANCE_SOON: { label: "صيانة قريبة", cls: "warn" },
  MAINTENANCE_DUE: { label: "صيانة مستحقة", cls: "err" },
  MAINTENANCE_OVERDUE: { label: "متأخرة", cls: "err" },
  FAULT: { label: "عطل", cls: "err" },
  UNKNOWN: { label: "غير محددة", cls: "muted" },
};

const EQUIP_LABEL: Record<string, string> = {
  MAIN_PUMP: "مضخة رئيسية",
  SUBMERSIBLE_PUMP: "مضخة غاطسة",
  FILTER: "فلتر",
};

function healthBadge(status: string) {
  const info = HEALTH[status] ?? { label: status, cls: "muted" };
  return <span className={`badge ${info.cls}`}>{info.label}</span>;
}

function fmtHours(v: number | null): string {
  if (v == null) return "—";
  return new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 }).format(v) + " س";
}

export default function AssetsPage() {
  const [assets, setAssets] = useState<AssetRow[] | null>(null);
  const [detail, setDetail] = useState<AssetDetail | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      setAssets(await api<AssetRow[]>("/api/assets"));
    } catch (e) {
      setError(String((e as Error).message ?? e));
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const open = async (code: string) => {
    setBusy(code);
    setError(null);
    try {
      setDetail(await api<AssetDetail>(`/api/assets/${encodeURIComponent(code)}`));
    } catch (e) {
      setError(String((e as Error).message ?? e));
    } finally {
      setBusy(null);
    }
  };

  return (
    <div>
      <h2 className="page-title">الأصول — حالة الصيانة</h2>
      <p className="page-desc">
        حالة كل مضخة/فلتر محسوبة من: قواعد المانوال المعتمدة + آخر صيانة + ساعات التشغيل + القراءات والعطلات
        (محرك حتمي — §8.3).
      </p>

      <div className="toolbar">
        <button className="btn" onClick={() => void load()}>
          تحديث
        </button>
      </div>

      {error && <div className="error-box">{error}</div>}
      {!assets && !error && <div className="loading">جارٍ التحميل…</div>}
      {assets && assets.length === 0 && (
        <div className="card">
          <div className="empty">لا توجد أصول بعد — تظهر تلقائيًا بعد استيراد أول حزمة زيارة.</div>
        </div>
      )}

      {assets && assets.length > 0 && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>الأصل</th>
                <th>الموقع</th>
                <th>النوع</th>
                <th>الموديل</th>
                <th>ساعات التشغيل</th>
                <th>الحالة</th>
                <th>المتبقي</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {assets.map((a) => (
                <tr key={a.asset_code}>
                  <td className="mono">{a.asset_code}</td>
                  <td className="mono">{a.location_code}</td>
                  <td>{EQUIP_LABEL[a.kind] ?? a.kind}</td>
                  <td className="muted">{a.model || "—"}</td>
                  <td>{fmtHours(a.health?.current_hours ?? a.running_hours)}</td>
                  <td>{healthBadge(a.health?.status ?? "UNKNOWN")}</td>
                  <td>
                    {a.health?.hours_remaining != null ? fmtHours(a.health.hours_remaining) : "—"}
                  </td>
                  <td>
                    <button className="btn" onClick={() => void open(a.asset_code)} disabled={busy === a.asset_code}>
                      {busy === a.asset_code ? "…" : "تفاصيل"}
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
            <h3 style={{ margin: 0 }}>{detail.asset_code}</h3>
            {healthBadge(detail.health.status)}
            <button className="btn" onClick={() => setDetail(null)}>
              إغلاق
            </button>
          </div>
          {detail.health.note && <p className="muted" style={{ margin: "0 0 8px", fontSize: 13 }}>⚠ {detail.health.note}</p>}

          <div className="kv" style={{ marginBottom: 12 }}>
            <span className="k">ساعات التشغيل الحالية:</span>
            <strong>{fmtHours(detail.health.current_hours)}</strong>
            {detail.health.baseline_hours != null && (
              <>
                <span className="k">نقطة البداية:</span>
                <span className="muted">{fmtHours(detail.health.baseline_hours)}</span>
              </>
            )}
            {detail.health.due_at_hours != null && (
              <>
                <span className="k">الصيانة القادمة عند:</span>
                <span className="muted">{fmtHours(detail.health.due_at_hours)}</span>
              </>
            )}
            {detail.health.hours_remaining != null && (
              <>
                <span className="k">المتبقي:</span>
                <span className="muted">{fmtHours(detail.health.hours_remaining)}</span>
              </>
            )}
          </div>

          <h3>القواعد المطبقة ({detail.health.rules_count})</h3>
          {detail.health.rules.length === 0 ? (
            <div className="empty" style={{ padding: "10px 0" }}>
              لا توجد قواعد معتمدة لهذا النوع والموديل — اعتمد القواعد من تبويب المانوالات.
            </div>
          ) : (
            <div className="table-wrap" style={{ marginBottom: 14 }}>
              <table>
                <thead>
                  <tr>
                    <th>النوع</th>
                    <th>الفترة</th>
                    <th>الوصف</th>
                    <th>المرجع</th>
                    <th>الحالة</th>
                    <th>المتبقي</th>
                  </tr>
                </thead>
                <tbody>
                  {detail.health.rules.map((r) => (
                    <tr key={r.rule_id}>
                      <td>{r.maintenance_type || "—"}</td>
                      <td>
                        {r.interval_hours ? `كل ${fmtHours(r.interval_hours)}` : r.interval_days ? `كل ${r.interval_days} يوم` : "—"}
                      </td>
                      <td className="muted" style={{ maxWidth: 260, fontSize: 12.5 }}>
                        {r.description || "—"}
                      </td>
                      <td className="muted" style={{ fontSize: 12.5 }}>
                        {r.source_page != null ? `ص ${r.source_page}` : "—"}
                        {r.source_section ? ` · ${r.source_section}` : ""}
                        {r.manual_id != null ? ` · Manual #${r.manual_id}` : ""}
                      </td>
                      <td>{healthBadge(r.status)}</td>
                      <td>{r.hours_remaining != null ? fmtHours(r.hours_remaining) : "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <h3>سجل القراءات ({detail.health.readings_count})</h3>
          {detail.health.readings.length === 0 ? (
            <div className="empty" style={{ padding: "10px 0" }}>لا توجد قراءات مسجّلة.</div>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>الزيارة</th>
                    <th>التاريخ</th>
                    <th>ساعات التشغيل</th>
                    <th>الضغط (bar)</th>
                    <th>حالة القراءة</th>
                  </tr>
                </thead>
                <tbody>
                  {detail.health.readings.map((r, i) => (
                    <tr key={i}>
                      <td className="mono">{r.visit_id}</td>
                      <td className="muted">{r.at}</td>
                      <td>{fmtHours(r.hours)}</td>
                      <td>{r.pressure_bar ?? "—"}</td>
                      <td>
                        <span className={`badge ${(r.status || "").toUpperCase() === "FAULT" ? "err" : "ok"}`}>
                          {r.status || "—"}
                        </span>
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
