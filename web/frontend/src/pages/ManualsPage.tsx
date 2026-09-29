import { useCallback, useEffect, useState } from "react";
import { api, type ManualRow, type SearchHit } from "../api";

function Snippet({ text }: { text: string }) {
  // إبراز [..] القادمة من snippet في FTS5
  const parts = text.split(/[\[\]]/);
  return (
    <span>
      {parts.map((p, i) =>
        i % 2 === 1 ? <mark key={i}>{p}</mark> : <span key={i}>{p}</span>,
      )}
    </span>
  );
}

export default function ManualsPage() {
  const [manuals, setManuals] = useState<ManualRow[] | null>(null);
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState<SearchHit[] | null>(null);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadManuals = useCallback(async () => {
    try {
      setManuals(await api<ManualRow[]>("/api/manuals"));
    } catch (e) {
      setError(String((e as Error).message ?? e));
    }
  }, []);

  useEffect(() => {
    void loadManuals();
  }, [loadManuals]);

  const search = async () => {
    const q = query.trim();
    if (!q) {
      setHits(null);
      return;
    }
    setSearching(true);
    setError(null);
    try {
      setHits(await api<SearchHit[]>(`/api/manuals/search?q=${encodeURIComponent(q)}&limit=20`));
    } catch (e) {
      setError(String((e as Error).message ?? e));
    } finally {
      setSearching(false);
    }
  };

  return (
    <div>
      <h2 className="page-title">المانوالات — البحث الشامل</h2>
      <p className="page-desc">
        ابحث في نصوص المانوالات المرفوعة (فهرسة FTS5) — النتائج تعرض الصفحة والقسم والمقتطف.
      </p>

      <div className="toolbar">
        <input
          type="search"
          placeholder="ابحث… مثال: bearing clearance"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") void search();
          }}
        />
        <button className="btn primary" onClick={() => void search()} disabled={searching}>
          {searching ? "جارٍ البحث…" : "ابحث"}
        </button>
        {hits && (
          <button
            className="btn"
            onClick={() => {
              setHits(null);
              setQuery("");
            }}
          >
            مسح النتائج
          </button>
        )}
      </div>

      {error && <div className="error-box">{error}</div>}

      {hits && (
        <div style={{ marginBottom: 22 }}>
          <h3 className="page-title" style={{ fontSize: 15 }}>
            نتائج البحث ({hits.length})
          </h3>
          {hits.length === 0 ? (
            <div className="card">
              <div className="empty">لا توجد نتائج مطابقة.</div>
            </div>
          ) : (
            hits.map((h) => (
              <div className="hit" key={h.chunk_id}>
                <div className="meta">
                  <span className="badge info">{h.manual_title}</span>
                  <span>صفحة {h.page}</span>
                  {h.section && <span>قسم: {h.section}</span>}
                </div>
                <div className="snippet">
                  <Snippet text={h.snippet || h.text} />
                </div>
              </div>
            ))
          )}
        </div>
      )}

      <h3 className="page-title" style={{ fontSize: 15 }}>
        كل المانوالات
      </h3>
      {!manuals && !error && <div className="loading">جارٍ التحميل…</div>}
      {manuals && manuals.length === 0 && (
        <div className="card">
          <div className="empty">
            لا توجد مانوالات بعد — ارفع أول PDF عبر POST /api/manuals وسيظهر هنا فورًا.
          </div>
        </div>
      )}
      {manuals && manuals.length > 0 && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>العنوان</th>
                <th>الشركة</th>
                <th>الموديل</th>
                <th>النوع</th>
                <th>الإصدار</th>
                <th>المقاطع</th>
                <th>الحالة</th>
              </tr>
            </thead>
            <tbody>
              {manuals.map((m) => (
                <tr key={m.id}>
                  <td style={{ fontWeight: 600 }}>{m.title}</td>
                  <td className="muted">{m.manufacturer || "—"}</td>
                  <td className="muted">{m.model || "—"}</td>
                  <td className="muted">{m.equipment_kind || "—"}</td>
                  <td className="muted">{m.revision || "—"}</td>
                  <td>{m.chunks}</td>
                  <td>
                    <span className="badge ok">{m.status}</span>
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
