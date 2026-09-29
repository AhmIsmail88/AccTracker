import { useEffect, useState } from "react";
import { api, countTree, type CloudStatus, type ConflictRow, type ImportRow, type TreeNode } from "../api";

function badgeForStatus(status: string) {
  switch (status) {
    case "IMPORTED":
      return <span className="badge ok">مستوردة</span>;
    case "DUPLICATE":
      return <span className="badge muted">مكررة</span>;
    case "REJECTED":
      return <span className="badge err">مرفوضة</span>;
    case "FAILED":
      return <span className="badge err">فاشلة</span>;
    default:
      return <span className="badge info">{status}</span>;
  }
}

export default function DashboardPage() {
  const [tree, setTree] = useState<TreeNode[] | null>(null);
  const [imports, setImports] = useState<ImportRow[] | null>(null);
  const [cloud, setCloud] = useState<CloudStatus | null>(null);
  const [conflicts, setConflicts] = useState<ConflictRow[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const [t, im, c, cf] = await Promise.all([
          api<TreeNode[]>("/api/locations/tree"),
          api<ImportRow[]>("/api/imports"),
          api<CloudStatus>("/api/cloud/status").catch(() => null),
          api<ConflictRow[]>("/api/locations/conflicts").catch(() => []),
        ]);
        setTree(t);
        setImports(im);
        setCloud(c);
        setConflicts(cf);
      } catch (e) {
        setError(String((e as Error).message ?? e));
      }
    })();
  }, []);

  if (error) {
    return <div className="error-box">تعذّر الاتصال بالخادم: {error} — تأكد أن الباك-إند يعمل على المنفذ 8000.</div>;
  }
  if (!tree || !imports) {
    return <div className="loading">جارٍ التحميل…</div>;
  }

  const counts = countTree(tree);
  const importedOk = imports.filter((r) => r.status === "IMPORTED").length;
  const lastImport = imports[0];

  return (
    <div>
      <h2 className="page-title">لوحة المتابعة</h2>
      <p className="page-desc">نظرة عامة على الشجرة والحزم الواردة وحالة المزامنة السحابية.</p>

      <div className="grid cols-4">
        <div className="card stat brand">
          <div className="value">{counts.projects}</div>
          <div className="label">مشاريع</div>
        </div>
        <div className="card stat">
          <div className="value">
            {counts.regions} · {counts.zones}
          </div>
          <div className="label">مناطق · زونات</div>
        </div>
        <div className="card stat">
          <div className="value">{counts.locations}</div>
          <div className="label">مواقع مسجّلة</div>
        </div>
        <div className="card stat">
          <div className="value">{importedOk}</div>
          <div className="label">حزم مستوردة</div>
        </div>
      </div>

      <div className="grid cols-2" style={{ marginTop: 16 }}>
        <div className="card">
          <h3>آخر الحزم الواردة</h3>
          {imports.length === 0 ? (
            <div className="empty">لا توجد حزم بعد — أول ما الفني يصدّر زيارة هتظهر هنا.</div>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>الحزمة</th>
                    <th>الحالة</th>
                    <th>التاريخ</th>
                  </tr>
                </thead>
                <tbody>
                  {imports.slice(0, 6).map((r) => (
                    <tr key={r.id}>
                      <td>
                        <span className="mono">{r.filename || r.package_id}</span>
                      </td>
                      <td>{badgeForStatus(r.status)}</td>
                      <td className="muted">{r.imported_at}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <div className="card">
          <h3>حالة المزامنة السحابية</h3>
          {cloud ? (
            cloud.configured ? (
              <p>
                <span className="badge ok">مفعّلة</span>{" "}
                <span className="muted">— الأجهزة ترفع الحزم تلقائيًا إلى Firebase، واسحبها من تبويب «المزامنة السحابية».</span>
              </p>
            ) : (
              <p>
                <span className="badge warn">بانتظار الإعداد</span>{" "}
                <span className="muted">
                  — ضع ملف service account في الخادم لتفعيل سحب الحزم من Firebase.
                </span>
              </p>
            )
          ) : (
            <div className="empty">تعذّر قراءة حالة المزامنة.</div>
          )}

          <h3 style={{ marginTop: 18 }}>تعارضات مفتوحة</h3>
          {conflicts.length === 0 ? (
            <div className="empty" style={{ padding: "12px 0" }}>
              لا توجد تعارضات مفتوحة 🎉
            </div>
          ) : (
            <ul style={{ margin: 0, paddingInlineStart: 18, fontSize: 13.5 }}>
              {conflicts.slice(0, 6).map((c) => (
                <li key={c.id} style={{ marginBottom: 6 }}>
                  <span className="badge warn">{c.type}</span> <span className="mono">{c.code}</span>
                </li>
              ))}
            </ul>
          )}

          {lastImport && (
            <>
              <h3 style={{ marginTop: 18 }}>آخر استيراد</h3>
              <div className="kv">
                <span className="k">الحزمة:</span>
                <span className="mono">{lastImport.package_id}</span>
              </div>
              <div className="kv">
                <span className="k">محتوى:</span>
                <span className="muted">
                  {Object.entries(lastImport.counts ?? {})
                    .map(([k, v]) => `${k}: ${v}`)
                    .join(" · ") || "—"}
                </span>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
