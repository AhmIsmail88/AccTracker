import { useCallback, useEffect, useState } from "react";
import {
  api,
  type PurchaseSuggestion,
  type SparePartRow,
  type StockMovementRow,
} from "../api";

const MTYPE_LABEL: Record<string, { label: string; cls: string }> = {
  IN: { label: "استلام", cls: "ok" },
  OUT: { label: "صرف", cls: "err" },
  RETURN: { label: "إرجاع", cls: "warn" },
  ADJUST: { label: "تسوية", cls: "info" },
};

function fmtQty(v: number | null | undefined, unit?: string | null): string {
  if (v == null) return "—";
  const n = new Intl.NumberFormat("en-US", { maximumFractionDigits: 2 }).format(v);
  return unit ? `${n} ${unit}` : n;
}

export default function StockPage() {
  const [parts, setParts] = useState<SparePartRow[] | null>(null);
  const [movements, setMovements] = useState<StockMovementRow[]>([]);
  const [suggestions, setSuggestions] = useState<PurchaseSuggestion[]>([]);
  const [lowOnly, setLowOnly] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  // نماذج الإضافة
  const [pCode, setPCode] = useState("");
  const [pName, setPName] = useState("");
  const [pMin, setPMin] = useState("2");
  const [pCost, setPCost] = useState("");
  const [mPartId, setMPartId] = useState("");
  const [mType, setMType] = useState("IN");
  const [mQty, setMQty] = useState("1");
  const [mRef, setMRef] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [p, m, s] = await Promise.all([
        api<SparePartRow[]>(`/api/stock/parts${lowOnly ? "?low_only=true" : ""}`),
        api<StockMovementRow[]>("/api/stock/movements?limit=30"),
        api<PurchaseSuggestion[]>("/api/stock/suggestions"),
      ]);
      setParts(p);
      setMovements(m);
      setSuggestions(s);
    } catch (e) {
      setError(String((e as Error).message ?? e));
    }
  }, [lowOnly]);

  useEffect(() => {
    void load();
  }, [load]);

  const addPart = async () => {
    if (!pCode.trim() || !pName.trim()) {
      setError("كود القطعة والاسم مطلوبان");
      return;
    }
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await api<SparePartRow>("/api/stock/parts", {
        method: "POST",
        body: JSON.stringify({
          part_code: pCode.trim(),
          name: pName.trim(),
          min_stock: Number(pMin) || 0,
          unit_cost: pCost.trim() ? Number(pCost) : null,
        }),
      });
      setNotice(`أُضيفت القطعة ${pCode.trim()}`);
      setPCode("");
      setPName("");
      setPMin("2");
      setPCost("");
      await load();
    } catch (e) {
      setError(String((e as Error).message ?? e));
    } finally {
      setBusy(false);
    }
  };

  const addMovement = async () => {
    if (!mPartId) {
      setError("اختر القطعة أولًا");
      return;
    }
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const res = await api<{ stock_after: number }>("/api/stock/movements", {
        method: "POST",
        body: JSON.stringify({
          part_id: Number(mPartId),
          movement_type: mType,
          qty: Number(mQty) || 0,
          reference: mRef.trim(),
        }),
      });
      setNotice(`تمت الحركة — الرصيد الجديد: ${res.stock_after}`);
      setMQty("1");
      setMRef("");
      await load();
    } catch (e) {
      setError(String((e as Error).message ?? e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      <h2 className="page-title">المخزون — قطع الغيار</h2>
      <p className="page-desc">
        رصيد كل قطعة محسوب من حركاتها (استلام/صرف/إرجاع/تسوية) + اقتراحات شراء تلقائية عند بلوغ حد إعادة الطلب.
      </p>

      {error && <div className="error-box">{error}</div>}
      {notice && (
        <div className="card" style={{ background: "#e8f5e9", borderColor: "#c8e6c9", color: "#2e7d32", marginBottom: 12, padding: "10px 14px" }}>
          {notice}
        </div>
      )}

      {suggestions.length > 0 && (
        <div className="card" style={{ borderColor: "#ffe0b2", background: "#fff8e1", marginBottom: 14 }}>
          <h3 style={{ marginTop: 0 }}>🛒 اقتراحات شراء ({suggestions.length})</h3>
          <div className="table-wrap" style={{ background: "transparent", border: "none" }}>
            <table>
              <thead>
                <tr>
                  <th>القطعة</th>
                  <th>الرصيد</th>
                  <th>حد الطلب</th>
                  <th>الكمية المقترحة</th>
                  <th>تكلفة تقديرية</th>
                </tr>
              </thead>
              <tbody>
                {suggestions.map((s) => (
                  <tr key={s.part_id}>
                    <td>
                      <span className="mono">{s.part_code}</span> — {s.name}
                    </td>
                    <td>{fmtQty(s.stock, s.unit)}</td>
                    <td>{fmtQty(s.min_stock, s.unit)}</td>
                    <td>
                      <strong>{fmtQty(s.suggested_qty, s.unit)}</strong>
                    </td>
                    <td>{s.est_cost != null ? `${s.est_cost} ج.م` : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <div className="grid cols-2">
        <div className="card">
          <h3>إضافة قطعة جديدة</h3>
          <div className="form-grid">
            <input placeholder="كود القطعة (BRG-6205)" value={pCode} onChange={(e) => setPCode(e.target.value)} />
            <input placeholder="الاسم" value={pName} onChange={(e) => setPName(e.target.value)} />
            <input placeholder="حد إعادة الطلب" type="number" value={pMin} onChange={(e) => setPMin(e.target.value)} />
            <input placeholder="تكلفة الوحدة (اختياري)" type="number" value={pCost} onChange={(e) => setPCost(e.target.value)} />
          </div>
          <button className="btn primary" onClick={() => void addPart()} disabled={busy} style={{ marginTop: 10 }}>
            إضافة القطعة
          </button>
        </div>

        <div className="card">
          <h3>حركة مخزون</h3>
          <div className="form-grid">
            <select value={mPartId} onChange={(e) => setMPartId(e.target.value)}>
              <option value="">— اختر القطعة —</option>
              {(parts ?? []).map((p) => (
                <option key={p.id} value={p.id}>
                  {p.part_code} — {p.name} (رصيد {p.stock ?? 0})
                </option>
              ))}
            </select>
            <select value={mType} onChange={(e) => setMType(e.target.value)}>
              <option value="IN">استلام (IN)</option>
              <option value="OUT">صرف (OUT)</option>
              <option value="RETURN">إرجاع (RETURN)</option>
              <option value="ADJUST">تسوية (ADJUST)</option>
            </select>
            <input placeholder="الكمية" type="number" value={mQty} onChange={(e) => setMQty(e.target.value)} />
            <input placeholder="مرجع (PO-123)" value={mRef} onChange={(e) => setMRef(e.target.value)} />
          </div>
          <button className="btn primary" onClick={() => void addMovement()} disabled={busy} style={{ marginTop: 10 }}>
            تسجيل الحركة
          </button>
        </div>
      </div>

      <div className="card" style={{ marginTop: 16 }}>
        <div className="detail-head">
          <h3 style={{ margin: 0 }}>القطع ({parts?.length ?? 0})</h3>
          <button className={`btn ${lowOnly ? "primary" : ""}`} onClick={() => setLowOnly(!lowOnly)}>
            {lowOnly ? "إظهار الكل" : "النواقص فقط"}
          </button>
        </div>
        {!parts && <div className="loading">جارٍ التحميل…</div>}
        {parts && parts.length === 0 && <div className="empty">لا توجد قطع — أضف أول قطعة من النموذج اليمين.</div>}
        {parts && parts.length > 0 && (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>الكود</th>
                  <th>الاسم</th>
                  <th>الرصيد</th>
                  <th>حد الطلب</th>
                  <th>تكلفة الوحدة</th>
                  <th>الحالة</th>
                </tr>
              </thead>
              <tbody>
                {parts.map((p) => (
                  <tr key={p.id}>
                    <td className="mono">{p.part_code}</td>
                    <td>{p.name}</td>
                    <td>{fmtQty(p.stock, p.unit)}</td>
                    <td className="muted">{fmtQty(p.min_stock, p.unit)}</td>
                    <td className="muted">{p.unit_cost != null ? `${p.unit_cost} ج.م` : "—"}</td>
                    <td>
                      {p.low_stock ? <span className="badge warn">يحتاج شراء</span> : <span className="badge ok">متاح</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="card" style={{ marginTop: 16 }}>
        <h3>آخر الحركات</h3>
        {movements.length === 0 ? (
          <div className="empty">لا توجد حركات بعد.</div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>القطعة</th>
                  <th>النوع</th>
                  <th>الكمية</th>
                  <th>أمر العمل</th>
                  <th>مرجع</th>
                  <th>التاريخ</th>
                </tr>
              </thead>
              <tbody>
                {movements.map((m) => {
                  const t = MTYPE_LABEL[m.movement_type] ?? { label: m.movement_type, cls: "muted" };
                  return (
                    <tr key={m.id}>
                      <td>
                        <span className="mono">{m.part_code}</span> — {m.part_name}
                      </td>
                      <td>
                        <span className={`badge ${t.cls}`}>{t.label}</span>
                      </td>
                      <td>{fmtQty(m.qty)}</td>
                      <td className="mono muted">{m.work_order_id ?? "—"}</td>
                      <td className="muted">{m.reference ?? "—"}</td>
                      <td className="muted" style={{ fontSize: 12 }}>
                        {m.created_at}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
