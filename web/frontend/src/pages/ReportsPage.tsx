import { useCallback, useEffect, useState } from "react";
import { api, type ReportTable } from "../api";

const KIND_LABEL: Record<string, string> = {
  SUMMARY: "الملخص العام",
  ASSETS: "حالة الأصول",
  WORK_ORDERS: "أوامر العمل",
  STOCK: "المخزون",
  VISITS: "الزيارات",
  ALERTS: "التنبيهات",
};

const STATUS_AR: Record<string, string> = {
  NORMAL: "سليمة",
  MAINTENANCE_SOON: "صيانة قريبة",
  MAINTENANCE_DUE: "صيانة مستحقة",
  MAINTENANCE_OVERDUE: "متأخرة",
  FAULT: "عطل",
  UNKNOWN: "غير محددة",
};

const COL_AR: Record<string, string> = {
  asset_code: "الأصل",
  location_code: "الموقع",
  kind: "النوع",
  model: "الموديل",
  status: "الحالة",
  current_hours: "ساعات التشغيل",
  hours_remaining: "المتبقي",
  due_at_hours: "الموعد",
  rules_count: "القواعد",
  last_reading_at: "آخر قراءة",
  wo_number: "الرقم",
  title: "العنوان",
  priority: "الأولوية",
  opened_at: "فتح",
  closed_at: "إغلاق",
  parts_count: "القطع",
  parts_cost: "التكلفة",
  part_code: "الكود",
  name: "الاسم",
  unit: "الوحدة",
  stock: "الرصيد",
  min_stock: "حد الطلب",
  low_stock: "ناقص",
  unit_cost: "تكلفة الوحدة",
  stock_value: "قيمة الرصيد",
  visit_id: "الزيارة",
  visit_type: "النوع",
  started_at: "البداية",
  equipment: "المعدات",
  checklist: "الفحوص",
  faults: "أعطال",
  package_id: "الحزمة",
  type: "النوع",
  severity: "الشدة",
  detail: "التفاصيل",
  at: "التاريخ",
};

function cell(v: unknown): string {
  if (v == null || v === "") return "—";
  if (typeof v === "boolean") return v ? "نعم" : "لا";
  const s = String(v);
  return STATUS_AR[s] ?? s;
}

export default function ReportsPage() {
  const [kind, setKind] = useState("SUMMARY");
  const [data, setData] = useState<ReportTable | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (k: string) => {
    setLoading(true);
    setError(null);
    try {
      setData(await api<ReportTable>(`/api/reports/${k}`));
    } catch (e) {
      setError(String((e as Error).message ?? e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load(kind);
  }, [kind, load]);

  const exportCsv = () => {
    window.open(`/api/reports/${kind}/export.csv`, "_blank");
  };

  return (
    <div>
      <h2 className="page-title">التقارير (§15)</h2>
      <p className="page-desc">
        تقارير جاهزة من بيانات النظام الحية — عرض مباشر + تصدير CSV يفتح في Excel.
      </p>

      <div className="toolbar">
        {Object.entries(KIND_LABEL).map(([k, label]) => (
          <button key={k} className={`btn ${kind === k ? "primary" : ""}`} onClick={() => setKind(k)}>
            {label}
          </button>
        ))}
      </div>

      <div className="toolbar">
        <button className="btn" onClick={() => void load(kind)} disabled={loading}>
          تحديث
        </button>
        <button className="btn primary" onClick={exportCsv}>
          تصدير CSV (Excel)
        </button>
        {data && (
          <span className="muted" style={{ fontSize: 12.5 }}>
            آخر توليد: {data.generated_at}
          </span>
        )}
      </div>

      {error && <div className="error-box">{error}</div>}
      {loading && <div className="loading">جارٍ التوليد…</div>}

      {data && !loading && kind === "SUMMARY" && (
        <div>
          <div className="grid cols-4">
            <div className="card stat brand">
              <div className="value">{data.counts?.locations ?? 0}</div>
              <div className="label">مواقع</div>
            </div>
            <div className="card stat">
              <div className="value">{data.counts?.assets ?? 0}</div>
              <div className="label">أصول</div>
            </div>
            <div className="card stat">
              <div className="value">{data.counts?.visits ?? 0}</div>
              <div className="label">زيارات</div>
            </div>
            <div className="card stat">
              <div className="value">{data.counts?.work_orders_open ?? 0}</div>
              <div className="label">أوامر عمل مفتوحة</div>
            </div>
          </div>
          <div className="grid cols-2" style={{ marginTop: 14 }}>
            <div className="card">
              <h3>حالات الأصول</h3>
              {Object.entries(data.asset_status ?? {}).map(([k, v]) => (
                <div key={k} className="kv" style={{ justifyContent: "space-between", marginBottom: 6 }}>
                  <span>{STATUS_AR[k] ?? k}</span>
                  <strong>{v}</strong>
                </div>
              ))}
            </div>
            <div className="card">
              <h3>المخزون والتنبيهات</h3>
              <div className="kv" style={{ justifyContent: "space-between", marginBottom: 6 }}>
                <span>قيمة المخزون</span>
                <strong>{data.stock?.stock_value ?? 0} ج.م</strong>
              </div>
              <div className="kv" style={{ justifyContent: "space-between", marginBottom: 6 }}>
                <span>قطع تحت حد الطلب</span>
                <strong>{data.stock?.low_stock_parts ?? 0}</strong>
              </div>
              <div className="kv" style={{ justifyContent: "space-between", marginBottom: 6 }}>
                <span>تنبيهات حرجة</span>
                <strong>{data.alerts?.CRITICAL ?? 0}</strong>
              </div>
              <div className="kv" style={{ justifyContent: "space-between" }}>
                <span>إجمالي التنبيهات</span>
                <strong>{data.alerts?.total ?? 0}</strong>
              </div>
            </div>
          </div>
        </div>
      )}

      {data && !loading && kind !== "SUMMARY" && data.columns && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                {data.columns.map((c) => (
                  <th key={c}>{COL_AR[c] ?? c}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {(data.rows ?? []).map((row, i) => (
                <tr key={i}>
                  {data.columns!.map((c) => (
                    <td key={c} className={c.endsWith("_code") || c.endsWith("_number") || c.endsWith("_id") ? "mono" : ""}>
                      {cell(row[c])}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
          {(data.rows ?? []).length === 0 && <div className="empty">لا توجد بيانات في هذا التقرير بعد.</div>}
        </div>
      )}

      {data && !loading && kind === "STOCK" && (data.suggestions ?? []).length > 0 && (
        <div className="card" style={{ marginTop: 14, borderColor: "#ffe0b2", background: "#fff8e1" }}>
          <h3 style={{ marginTop: 0 }}>🛒 اقتراحات شراء ({data.suggestions!.length})</h3>
          <div className="muted" style={{ fontSize: 13 }}>
            {data.suggestions!.map((s, i) => (
              <span key={i} style={{ marginInlineEnd: 12 }}>
                {String(s.part_code)} × {String(s.suggested_qty)}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
