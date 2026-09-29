import { useCallback, useEffect, useState } from "react";
import { api, type DeviceRow } from "../api";

export default function DevicesPage() {
  const [devices, setDevices] = useState<DeviceRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      setDevices(await api<DeviceRow[]>("/api/devices"));
    } catch (e) {
      setError(String((e as Error).message ?? e));
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div>
      <h2 className="page-title">الأجهزة والفنيون</h2>
      <p className="page-desc">
        كل جهاز رفع حزمًا من الميدان — آخر ظهور، عدد الحزم، والزيارات الواردة منه (لتتبع الأجهزة في الـLab).
      </p>

      <div className="toolbar">
        <button className="btn" onClick={() => void load()}>
          تحديث
        </button>
      </div>

      {error && <div className="error-box">{error}</div>}
      {!devices && !error && <div className="loading">جارٍ التحميل…</div>}
      {devices && devices.length === 0 && (
        <div className="card">
          <div className="empty">لا توجد أجهزة بعد — تظهر تلقائيًا بعد أول حزمة واردة.</div>
        </div>
      )}

      {devices && devices.length > 0 && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>الجهاز</th>
                <th>البصمة</th>
                <th>الحزم</th>
                <th>استيراد ناجح</th>
                <th>آخر ظهور</th>
                <th>آخر ملف</th>
                <th>زيارات</th>
              </tr>
            </thead>
            <tbody>
              {devices.map((d) => (
                <tr key={d.device_id}>
                  <td className="mono">{d.device_id || "—"}</td>
                  <td className="muted mono" style={{ fontSize: 12 }}>
                    {d.fingerprint ? d.fingerprint.slice(0, 18) + "…" : "—"}
                  </td>
                  <td>{d.packages}</td>
                  <td>
                    {d.imported_ok > 0 ? (
                      <span className="badge ok">{d.imported_ok}</span>
                    ) : (
                      <span className="badge muted">0</span>
                    )}
                  </td>
                  <td className="muted">{d.last_seen ?? "—"}</td>
                  <td className="muted mono" style={{ fontSize: 12 }}>
                    {d.last_file ?? "—"}
                  </td>
                  <td className="muted" style={{ fontSize: 12 }}>
                    {d.visits.slice(0, 3).join(", ")}
                    {d.visits.length > 3 ? "…" : ""}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
