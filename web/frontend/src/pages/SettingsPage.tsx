import { useCallback, useEffect, useState } from "react";
import { api, type SettingsResponse } from "../api";

const LABELS: Record<string, { title: string; desc: string; unit: string }> = {
  "maintenance.grace_hours": {
    title: "فترة سماح الصيانة (Grace Period)",
    desc: "ساعات إضافية بعد الاستحقاق قبل اعتبار الصيانة «متأخرة» — تخفف الضغط عن الورشة (§23).",
    unit: "ساعة",
  },
  "maintenance.soon_percent": {
    title: "عتبة «صيانة قريبة»",
    desc: "النسبة من فترة الصيانة التي يعتبر عندها النظام الصيانة «قريبة» (من 1% إلى 50%).",
    unit: "%",
  },
  "maintenance.soon_min_hours": {
    title: "الحد الأدنى لعتبة «قريبة»",
    desc: "للفترات القصيرة — أقل عدد ساعات يُعتبر «قريب» حتى لو كانت النسبة أقل.",
    unit: "ساعة",
  },
};

export default function SettingsPage() {
  const [data, setData] = useState<SettingsResponse | null>(null);
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const resp = await api<SettingsResponse>("/api/settings");
      setData(resp);
      const d: Record<string, string> = {};
      for (const [k, v] of Object.entries(resp.values)) d[k] = String(v);
      setDraft(d);
    } catch (e) {
      setError(String((e as Error).message ?? e));
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const save = async () => {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const patch: Record<string, number> = {};
      for (const [k, v] of Object.entries(draft)) {
        const num = Number(v);
        if (!Number.isNaN(num)) patch[k] = num;
      }
      const resp = await api<SettingsResponse>("/api/settings", {
        method: "PATCH",
        body: JSON.stringify(patch),
      });
      setData(resp);
      setNotice("تم حفظ الإعدادات — تسري فورًا على محرك الصيانة والتنبيهات.");
    } catch (e) {
      setError(String((e as Error).message ?? e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      <h2 className="page-title">الإعدادات</h2>
      <p className="page-desc">
        إعدادات محرك الصيانة الحتمي — تُطبق مباشرة على حالة الأصول والتنبيهات (بلا حاجة لإعادة تشغيل).
      </p>

      {error && <div className="error-box">{error}</div>}
      {notice && (
        <div className="card" style={{ background: "#e8f5e9", borderColor: "#c8e6c9", color: "#2e7d32", marginBottom: 12, padding: "10px 14px" }}>
          {notice}
        </div>
      )}
      {!data && !error && <div className="loading">جارٍ التحميل…</div>}

      {data && (
        <div className="card">
          {Object.keys(LABELS).map((key) => (
            <div key={key} style={{ marginBottom: 18 }}>
              <label style={{ fontWeight: 600, display: "block", marginBottom: 4 }}>
                {LABELS[key].title} <span className="muted">({LABELS[key].unit})</span>
              </label>
              <p className="muted" style={{ margin: "0 0 6px", fontSize: 12.5 }}>
                {LABELS[key].desc}
              </p>
              <input
                type="number"
                value={draft[key] ?? ""}
                onChange={(e) => setDraft((s) => ({ ...s, [key]: e.target.value }))}
                style={{ width: 180 }}
              />
            </div>
          ))}
          <button className="btn primary" onClick={() => void save()} disabled={busy}>
            {busy ? "جارٍ الحفظ…" : "حفظ الإعدادات"}
          </button>
        </div>
      )}
    </div>
  );
}
