import { useCallback, useEffect, useState } from "react";
import { api, type AiSuggestion, type AssetDetail, type AssetRow } from "../api";

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

function aiSeverityBadge(s: string) {
  const map: Record<string, { label: string; cls: string }> = {
    CRITICAL: { label: "حرج", cls: "err" },
    WARNING: { label: "تحذير", cls: "warn" },
    INFO: { label: "معلومة", cls: "info" },
  };
  const info = map[s] ?? { label: s, cls: "muted" };
  return <span className={`badge ${info.cls}`}>{info.label}</span>;
}

function confBadge(c: string) {
  const map: Record<string, { label: string; cls: string }> = {
    HIGH: { label: "ثقة عالية", cls: "ok" },
    MEDIUM: { label: "ثقة متوسطة", cls: "warn" },
    LOW: { label: "ثقة منخفضة", cls: "muted" },
  };
  const info = map[c] ?? { label: c, cls: "muted" };
  return <span className={`badge ${info.cls}`}>{info.label}</span>;
}

function aiStatusBadge(s: string) {
  const map: Record<string, { label: string; cls: string }> = {
    SUGGESTED: { label: "بانتظار قرار المهندس", cls: "info" },
    APPROVED: { label: "معتمد", cls: "ok" },
    REJECTED: { label: "مرفوض", cls: "muted" },
  };
  const info = map[s] ?? { label: s, cls: "muted" };
  return <span className={`badge ${info.cls}`}>{info.label}</span>;
}

export default function AssetsPage() {
  const [assets, setAssets] = useState<AssetRow[] | null>(null);
  const [detail, setDetail] = useState<AssetDetail | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [aiSugg, setAiSugg] = useState<AiSuggestion[] | null>(null);
  const [aiBusy, setAiBusy] = useState(false);
  const [aiError, setAiError] = useState<string | null>(null);

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
    setAiSugg(null);
    setAiError(null);
    try {
      setDetail(await api<AssetDetail>(`/api/assets/${encodeURIComponent(code)}`));
      try {
        setAiSugg(await api<AiSuggestion[]>(`/api/ai/suggestions?asset_code=${encodeURIComponent(code)}`));
      } catch {
        setAiSugg([]);
      }
    } catch (e) {
      setError(String((e as Error).message ?? e));
    } finally {
      setBusy(null);
    }
  };

  const runAi = async () => {
    if (!detail) return;
    setAiBusy(true);
    setAiError(null);
    try {
      const resp = await api<{ suggestion: AiSuggestion }>(
        `/api/ai/analyze/${encodeURIComponent(detail.asset_code)}`,
        { method: "POST" },
      );
      setAiSugg([resp.suggestion, ...(aiSugg ?? [])]);
    } catch (e) {
      setAiError(String((e as Error).message ?? e));
    } finally {
      setAiBusy(false);
    }
  };

  const reviewAi = async (id: number | undefined, status: "APPROVED" | "REJECTED") => {
    if (id == null) return;
    setAiError(null);
    try {
      const updated = await api<AiSuggestion>(`/api/ai/suggestions/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ status }),
      });
      setAiSugg((prev) =>
        (prev ?? []).map((s) => (s.id === id ? { ...s, status: updated.status, reviewed_at: updated.reviewed_at } : s)),
      );
    } catch (e) {
      setAiError(String((e as Error).message ?? e));
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

          <h3>التحليل الذكي — AI (§11)</h3>
          <p className="muted" style={{ fontSize: 12.5, margin: "0 0 10px" }}>
            مقترحات مبنية على المانوالات والقراءات — كل مقترح يحمل مرجعًا من المانوال (§16)، والقرار النهائي
            بيد المهندس (§14).
          </p>
          <div className="toolbar" style={{ marginBottom: 10 }}>
            <button className="btn primary" onClick={() => void runAi()} disabled={aiBusy}>
              {aiBusy ? "جارٍ التحليل… (قد يستغرق دقيقة)" : "اطلب تحليل AI"}
            </button>
          </div>
          {aiError && <div className="error-box">{aiError}</div>}
          {aiSugg && aiSugg.length === 0 && !aiBusy && (
            <div className="empty" style={{ padding: "10px 0" }}>
              لا توجد تحليلات لهذا الأصل بعد — اضغط «اطلب تحليل AI».
            </div>
          )}
          {aiSugg &&
            aiSugg.map((s) => (
              <div key={s.id} className="card" style={{ margin: "0 0 12px", background: "#fafafa" }}>
                <div className="detail-head" style={{ marginBottom: 6 }}>
                  {aiSeverityBadge(s.severity)}
                  {confBadge(s.confidence)}
                  {aiStatusBadge(s.status)}
                  {s.model_name && (
                    <span className="muted" style={{ fontSize: 11.5 }}>
                      {s.model_name}
                    </span>
                  )}
                  {s.created_at && (
                    <span className="muted" style={{ fontSize: 11.5 }}>
                      {s.created_at}
                    </span>
                  )}
                </div>
                {s.summary && <p style={{ margin: "4px 0 8px", fontSize: 13.5 }}>{s.summary}</p>}
                {s.reason.length > 0 && (
                  <ul style={{ margin: "0 0 8px", paddingInlineStart: 18, fontSize: 13 }}>
                    {s.reason.map((r, i) => (
                      <li key={i}>{r}</li>
                    ))}
                  </ul>
                )}
                {s.maintenance_suggestions.length > 0 && (
                  <div className="table-wrap" style={{ marginBottom: 8 }}>
                    <table>
                      <thead>
                        <tr>
                          <th>الإجراء المقترح</th>
                          <th>السبب</th>
                          <th>المرجع</th>
                        </tr>
                      </thead>
                      <tbody>
                        {s.maintenance_suggestions.map((a, i) => (
                          <tr key={i}>
                            <td style={{ fontSize: 13 }}>{a.action}</td>
                            <td className="muted" style={{ fontSize: 12.5 }}>
                              {a.reason}
                            </td>
                            <td className="muted mono" style={{ fontSize: 12 }}>
                              {a.source?.manual_id != null ? `Manual #${a.source.manual_id}` : "—"}
                              {a.source?.page != null ? ` · ص ${a.source.page}` : ""}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
                {s.evidence.length > 0 && (
                  <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 8 }}>
                    {s.evidence.map((e, i) => (
                      <span key={i} className={`badge ${e.verified ? "ok" : "muted"}`} style={{ fontSize: 11 }}>
                        {e.type}
                        {e.manual_id != null ? ` #${e.manual_id}` : ""}
                        {e.page != null ? ` ص${e.page}` : ""}
                        {e.asset_code ? ` ${e.asset_code}` : ""}
                        {e.verified === false ? " (غير موثَّق)" : ""}
                      </span>
                    ))}
                  </div>
                )}
                {s.status === "SUGGESTED" && s.id != null && (
                  <div className="toolbar" style={{ marginBottom: 0 }}>
                    <button className="btn primary" onClick={() => void reviewAi(s.id, "APPROVED")}>
                      اعتماد
                    </button>
                    <button className="btn" onClick={() => void reviewAi(s.id, "REJECTED")}>
                      رفض
                    </button>
                  </div>
                )}
                {s.reviewed_at && (
                  <p className="muted" style={{ fontSize: 11.5, margin: "6px 0 0" }}>
                    قرار المهندس: {s.reviewed_at}
                  </p>
                )}
              </div>
            ))}
        </div>
      )}
    </div>
  );
}
