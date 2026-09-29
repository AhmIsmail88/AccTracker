import { useCallback, useEffect, useState } from "react";
import { api, type ImportRow } from "../api";

function badgeForStatus(status: string) {
  switch (status) {
    case "IMPORTED":
      return <span className="badge ok">مستوردة</span>;
    case "DUPLICATE":
      return <span className="badge muted">مكررة (تم تجاهلها)</span>;
    case "REJECTED":
      return <span className="badge err">مرفوضة</span>;
    case "FAILED":
      return <span className="badge err">فاشلة التحقق</span>;
    default:
      return <span className="badge info">{status}</span>;
  }
}

export default function ImportsPage() {
  const [rows, setRows] = useState<ImportRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      setRows(await api<ImportRow[]>("/api/imports"));
    } catch (e) {
      setError(String((e as Error).message ?? e));
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div>
      <h2 className="page-title">الحزم المستوردة</h2>
      <p className="page-desc">سجل كل الحزم التي وصلت من أجهزة الفنيين — تظهر هنا فور استيرادها أو سحبها من السحابة.</p>

      <div className="toolbar">
        <button className="btn" onClick={() => void load()}>
          تحديث
        </button>
      </div>

      {error && <div className="error-box">تعذّر تحميل السجل: {error}</div>}
      {!rows && !error && <div className="loading">جارٍ التحميل…</div>}
      {rows && rows.length === 0 && (
        <div className="card">
          <div className="empty">لا توجد حزم بعد.</div>
        </div>
      )}
      {rows && rows.length > 0 && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>#</th>
                <th>الحزمة</th>
                <th>الجهاز</th>
                <th>الحالة</th>
                <th>المحتوى</th>
                <th>التاريخ</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id}>
                  <td className="muted">{r.id}</td>
                  <td>
                    <div className="mono">{r.package_id}</div>
                    <div className="muted" style={{ fontSize: 12 }}>
                      {r.filename}
                    </div>
                  </td>
                  <td className="muted">
                    <span className="mono">{(r.device_id || "").slice(0, 8)}</span>
                  </td>
                  <td>{badgeForStatus(r.status)}</td>
                  <td className="muted" style={{ fontSize: 12.5 }}>
                    {Object.entries(r.counts ?? {})
                      .filter(([k]) => k !== "schema_version")
                      .map(([k, v]) => `${k}: ${v}`)
                      .join(" · ") || "—"}
                  </td>
                  <td className="muted">{r.imported_at}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
