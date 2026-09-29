import { useCallback, useEffect, useState } from "react";
import { api, type SparePartRow, type WorkOrderRow } from "../api";

const STATUS: Record<string, { label: string; cls: string }> = {
  OPEN: { label: "مفتوح", cls: "info" },
  IN_PROGRESS: { label: "قيد التنفيذ", cls: "warn" },
  DONE: { label: "مكتمل", cls: "ok" },
  CANCELLED: { label: "ملغي", cls: "muted" },
};

const PRIORITY: Record<string, { label: string; cls: string }> = {
  LOW: { label: "منخفضة", cls: "muted" },
  MEDIUM: { label: "متوسطة", cls: "info" },
  HIGH: { label: "عالية", cls: "warn" },
  CRITICAL: { label: "حرجة", cls: "err" },
};

function fmtNum(v: number | null | undefined): string {
  if (v == null) return "—";
  return new Intl.NumberFormat("en-US", { maximumFractionDigits: 2 }).format(v);
}

export default function WorkOrdersPage() {
  const [works, setWorks] = useState<WorkOrderRow[] | null>(null);
  const [parts, setParts] = useState<SparePartRow[]>([]);
  const [detail, setDetail] = useState<WorkOrderRow | null>(null);
  const [statusFilter, setStatusFilter] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  // إنشاء أمر جديد
  const [assetCode, setAssetCode] = useState("");
  const [title, setTitle] = useState("");
  const [priority, setPriority] = useState("MEDIUM");
  const [desc, setDesc] = useState("");

  // إدارة قطع التفاصيل
  const [addPartId, setAddPartId] = useState("");
  const [addQty, setAddQty] = useState("1");
  const [issQty, setIssQty] = useState<Record<number, string>>({});
  const [retQty, setRetQty] = useState<Record<number, string>>({});

  const load = useCallback(async () => {
    setError(null);
    try {
      const url = statusFilter ? `/api/work-orders?status=${statusFilter}` : "/api/work-orders";
      const [w, p] = await Promise.all([
        api<WorkOrderRow[]>(url),
        api<SparePartRow[]>("/api/stock/parts"),
      ]);
      setWorks(w);
      setParts(p);
    } catch (e) {
      setError(String((e as Error).message ?? e));
    }
  }, [statusFilter]);

  useEffect(() => {
    void load();
  }, [load]);

  const openDetail = async (id: number) => {
    setBusy(true);
    setError(null);
    try {
      setDetail(await api<WorkOrderRow>(`/api/work-orders/${id}`));
    } catch (e) {
      setError(String((e as Error).message ?? e));
    } finally {
      setBusy(false);
    }
  };

  const create = async () => {
    if (!title.trim()) {
      setError("عنوان أمر العمل مطلوب");
      return;
    }
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const wo = await api<WorkOrderRow>("/api/work-orders", {
        method: "POST",
        body: JSON.stringify({
          title: title.trim(),
          asset_code: assetCode.trim(),
          priority,
          description: desc.trim(),
        }),
      });
      setNotice(`أُنشئ أمر العمل ${wo.wo_number}`);
      setTitle("");
      setAssetCode("");
      setDesc("");
      setPriority("MEDIUM");
      await load();
    } catch (e) {
      setError(String((e as Error).message ?? e));
    } finally {
      setBusy(false);
    }
  };

  const setStatus = async (id: number, status: string) => {
    setBusy(true);
    setError(null);
    try {
      const wo = await api<WorkOrderRow>(`/api/work-orders/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ status }),
      });
      setDetail(wo);
      await load();
    } catch (e) {
      setError(String((e as Error).message ?? e));
    } finally {
      setBusy(false);
    }
  };

  const planPart = async () => {
    if (!detail || !addPartId) return;
    setBusy(true);
    setError(null);
    try {
      setDetail(await api<WorkOrderRow>(`/api/work-orders/${detail.id}/parts`, {
        method: "POST",
        body: JSON.stringify({ part_id: Number(addPartId), planned_qty: Number(addQty) || 1 }),
      }));
      setAddQty("1");
    } catch (e) {
      setError(String((e as Error).message ?? e));
    } finally {
      setBusy(false);
    }
  };

  const doIssue = async (partId: number) => {
    if (!detail) return;
    setBusy(true);
    setError(null);
    try {
      setDetail(await api<WorkOrderRow>(`/api/work-orders/${detail.id}/parts/${partId}/issue`, {
        method: "POST",
        body: JSON.stringify({ qty: Number(issQty[partId]) || 1 }),
      }));
      setIssQty((s) => ({ ...s, [partId]: "" }));
    } catch (e) {
      setError(String((e as Error).message ?? e));
    } finally {
      setBusy(false);
    }
  };

  const doReturn = async (partId: number) => {
    if (!detail) return;
    setBusy(true);
    setError(null);
    try {
      setDetail(await api<WorkOrderRow>(`/api/work-orders/${detail.id}/parts/${partId}/return`, {
        method: "POST",
        body: JSON.stringify({ qty: Number(retQty[partId]) || 1 }),
      }));
      setRetQty((s) => ({ ...s, [partId]: "" }));
    } catch (e) {
      setError(String((e as Error).message ?? e));
    } finally {
      setBusy(false);
    }
  };

  const statusBadge = (s: string) => {
    const t = STATUS[s] ?? { label: s, cls: "muted" };
    return <span className={`badge ${t.cls}`}>{t.label}</span>;
  };
  const priorityBadge = (p: string) => {
    const t = PRIORITY[p] ?? { label: p, cls: "muted" };
    return <span className={`badge ${t.cls}`}>{t.label}</span>;
  };

  return (
    <div>
      <h2 className="page-title">أوامر العمل</h2>
      <p className="page-desc">
        من العطل إلى الإصلاح: إنشاء أمر، تخطيط قطع الغيار، إصدار/إرجاع من المخزون، ومتابعة التكلفة —
        والإغلاق يُسجَّل في تاريخ المعدة (§20/§21).
      </p>

      {error && <div className="error-box">{error}</div>}
      {notice && (
        <div className="card" style={{ background: "#e8f5e9", borderColor: "#c8e6c9", color: "#2e7d32", marginBottom: 12, padding: "10px 14px" }}>
          {notice}
        </div>
      )}

      <div className="card" style={{ marginBottom: 14 }}>
        <h3 style={{ marginTop: 0 }}>أمر عمل جديد</h3>
        <div className="form-grid">
          <input placeholder="كود الأصل (LOC-001-MP-03)" value={assetCode} onChange={(e) => setAssetCode(e.target.value)} />
          <input placeholder="العنوان — مثال: استبدال الختم الميكانيكي" value={title} onChange={(e) => setTitle(e.target.value)} />
          <select value={priority} onChange={(e) => setPriority(e.target.value)}>
            <option value="LOW">أولوية منخفضة</option>
            <option value="MEDIUM">أولوية متوسطة</option>
            <option value="HIGH">أولوية عالية</option>
            <option value="CRITICAL">أولوية حرجة</option>
          </select>
          <input placeholder="وصف مختصر (اختياري)" value={desc} onChange={(e) => setDesc(e.target.value)} />
        </div>
        <button className="btn primary" onClick={() => void create()} disabled={busy} style={{ marginTop: 10 }}>
          إنشاء الأمر
        </button>
      </div>

      <div className="toolbar">
        <button className={`btn ${statusFilter === "" ? "primary" : ""}`} onClick={() => setStatusFilter("")}>
          الكل
        </button>
        {Object.entries(STATUS).map(([id, t]) => (
          <button key={id} className={`btn ${statusFilter === id ? "primary" : ""}`} onClick={() => setStatusFilter(id)}>
            {t.label}
          </button>
        ))}
      </div>

      {!works && <div className="loading">جارٍ التحميل…</div>}
      {works && works.length === 0 && (
        <div className="card">
          <div className="empty">لا توجد أوامر عمل بعد — أنشئ أول أمر من النموذج بالأعلى.</div>
        </div>
      )}
      {works && works.length > 0 && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>الرقم</th>
                <th>العنوان</th>
                <th>الأصل</th>
                <th>الأولوية</th>
                <th>الحالة</th>
                <th>القطع/التكلفة</th>
                <th>التاريخ</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {works.map((w) => (
                <tr key={w.id}>
                  <td className="mono">{w.wo_number}</td>
                  <td>{w.title}</td>
                  <td className="mono muted">{w.asset_code ?? "—"}</td>
                  <td>{priorityBadge(w.priority)}</td>
                  <td>{statusBadge(w.status)}</td>
                  <td className="muted" style={{ fontSize: 12.5 }}>
                    {w.parts_count} قطعة · {fmtNum(w.parts_cost)} ج.م
                  </td>
                  <td className="muted" style={{ fontSize: 12 }}>
                    {w.opened_at}
                  </td>
                  <td>
                    <button className="btn" onClick={() => void openDetail(w.id)} disabled={busy}>
                      تفاصيل
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
            <h3 style={{ margin: 0 }}>
              {detail.wo_number} — {detail.title}
            </h3>
            {statusBadge(detail.status)}
            {priorityBadge(detail.priority)}
            <button className="btn" onClick={() => setDetail(null)}>
              إغلاق
            </button>
          </div>

          <div className="kv" style={{ marginBottom: 10 }}>
            {detail.asset_code && (
              <>
                <span className="k">الأصل:</span>
                <span className="mono">{detail.asset_code}</span>
              </>
            )}
            {detail.location_code && (
              <>
                <span className="k">الموقع:</span>
                <span className="mono">{detail.location_code}</span>
              </>
            )}
            <span className="k">فتح:</span>
            <span className="muted">{detail.opened_at}</span>
            {detail.closed_at && (
              <>
                <span className="k">إغلاق:</span>
                <span className="muted">{detail.closed_at}</span>
              </>
            )}
            <span className="k">التكلفة الفعلية:</span>
            <strong>{fmtNum(detail.parts_cost)} ج.م</strong>
          </div>
          {detail.description && <p className="muted" style={{ fontSize: 13 }}>{detail.description}</p>}
          {detail.closing_note && <p className="muted" style={{ fontSize: 13 }}>ملاحظة الإغلاق: {detail.closing_note}</p>}

          <div className="toolbar" style={{ marginBottom: 10 }}>
            {detail.status === "OPEN" && (
              <button className="btn" onClick={() => void setStatus(detail.id, "IN_PROGRESS")} disabled={busy}>
                بدء التنفيذ
              </button>
            )}
            {(detail.status === "OPEN" || detail.status === "IN_PROGRESS") && (
              <>
                <button className="btn primary" onClick={() => void setStatus(detail.id, "DONE")} disabled={busy}>
                  إغلاق كمكتمل
                </button>
                <button className="btn" onClick={() => void setStatus(detail.id, "CANCELLED")} disabled={busy}>
                  إلغاء
                </button>
              </>
            )}
          </div>

          <h3>قطع الغيار ({detail.parts?.length ?? 0})</h3>
          {(detail.status === "OPEN" || detail.status === "IN_PROGRESS") && (
            <div className="toolbar" style={{ marginBottom: 10 }}>
              <select value={addPartId} onChange={(e) => setAddPartId(e.target.value)}>
                <option value="">— اختر قطعة للتخطيط —</option>
                {parts.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.part_code} — {p.name} (رصيد {p.stock ?? 0})
                  </option>
                ))}
              </select>
              <input
                type="number"
                value={addQty}
                onChange={(e) => setAddQty(e.target.value)}
                style={{ width: 90 }}
                placeholder="كمية"
              />
              <button className="btn" onClick={() => void planPart()} disabled={busy || !addPartId}>
                تخطيط القطعة
              </button>
            </div>
          )}

          {(!detail.parts || detail.parts.length === 0) && (
            <div className="empty" style={{ padding: "10px 0" }}>لا توجد قطع مخططة.</div>
          )}
          {detail.parts && detail.parts.length > 0 && (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>القطعة</th>
                    <th>مخطط</th>
                    <th>مُصدَر</th>
                    <th>مرتجع</th>
                    <th>تكلفة</th>
                    <th>إجراءات</th>
                  </tr>
                </thead>
                <tbody>
                  {detail.parts.map((pr) => (
                    <tr key={pr.id}>
                      <td>
                        <span className="mono">{pr.part_code}</span> — {pr.part_name}
                      </td>
                      <td>{fmtNum(pr.planned_qty)}</td>
                      <td>
                        <strong>{fmtNum(pr.issued_qty)}</strong>
                      </td>
                      <td>{fmtNum(pr.returned_qty)}</td>
                      <td>{fmtNum(pr.cost)} ج.م</td>
                      <td>
                        {(detail.status === "OPEN" || detail.status === "IN_PROGRESS") && (
                          <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                            <input
                              type="number"
                              placeholder="كمية"
                              value={issQty[pr.part_id] ?? ""}
                              onChange={(e) => setIssQty((s) => ({ ...s, [pr.part_id]: e.target.value }))}
                              style={{ width: 70, padding: "6px 8px" }}
                            />
                            <button className="btn" onClick={() => void doIssue(pr.part_id)} disabled={busy}>
                              إصدار
                            </button>
                            <input
                              type="number"
                              placeholder="كمية"
                              value={retQty[pr.part_id] ?? ""}
                              onChange={(e) => setRetQty((s) => ({ ...s, [pr.part_id]: e.target.value }))}
                              style={{ width: 70, padding: "6px 8px" }}
                            />
                            <button className="btn" onClick={() => void doReturn(pr.part_id)} disabled={busy}>
                              إرجاع
                            </button>
                          </div>
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
