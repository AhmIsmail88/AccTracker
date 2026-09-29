import { useEffect, useState } from "react";
import { api, type TreeNode } from "../api";

const TYPE_LABEL: Record<string, string> = {
  PROJECT: "مشروع",
  REGION: "منطقة",
  ZONE: "زون",
  LOCATION: "موقع",
};

function NodeView({ node, depth }: { node: TreeNode; depth: number }) {
  const children =
    node.type === "PROJECT"
      ? node.regions ?? []
      : node.type === "REGION"
        ? node.zones ?? []
        : node.type === "ZONE"
          ? node.locations ?? []
          : [];
  const [open, setOpen] = useState(depth < 1);

  return (
    <div>
      <div className="tree-node">
        <div className="tree-row">
          {children.length > 0 ? (
            <button className="toggle" onClick={() => setOpen(!open)} title={open ? "طي" : "فتح"}>
              {open ? "▾" : "▸"}
            </button>
          ) : (
            <span className="toggle" />
          )}
          <span className="type-chip">{TYPE_LABEL[node.type] ?? node.type}</span>
          <span className="name">{node.name}</span>
          <span className="code">{node.code}</span>
          {node.status !== "ACTIVE" && <span className="badge muted">معطّل</span>}
          {node.review_status === "NEW_FROM_FIELD" && <span className="badge warn">جديد من الميدان</span>}
        </div>
        {open && children.length > 0 && (
          <div className="tree-children">
            {children.map((c) => (
              <NodeView key={c.code} node={c} depth={depth + 1} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default function LocationsPage() {
  const [tree, setTree] = useState<TreeNode[] | null>(null);
  const [includeInactive, setIncludeInactive] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const t = await api<TreeNode[]>(`/api/locations/tree?include_inactive=${includeInactive}`);
        if (alive) setTree(t);
      } catch (e) {
        if (alive) setError(String((e as Error).message ?? e));
      }
    })();
    return () => {
      alive = false;
    };
  }, [includeInactive]);

  return (
    <div>
      <h2 className="page-title">شجرة المواقع</h2>
      <p className="page-desc">
        عرض الشجرة الإدارية: مشروع ← منطقة ← زون ← موقع. العناصر «الجديدة من الميدان» تظهر للمراجعة.
      </p>

      <div className="toolbar">
        <button
          className="btn"
          onClick={() => {
            setTree(null);
            setError(null);
            setIncludeInactive(!includeInactive);
          }}
        >
          {includeInactive ? "إخفاء المعطّل" : "إظهار المعطّل"}
        </button>
      </div>

      {error && <div className="error-box">تعذّر تحميل الشجرة: {error}</div>}
      {!tree && !error && <div className="loading">جارٍ التحميل…</div>}
      {tree && tree.length === 0 && (
        <div className="card">
          <div className="empty">
            لا توجد عناصر بعد — أضف من تطبيق الفني أو أنشئ عبر الـAPI، وستظهر الحزم الواردة هنا تلقائيًا.
          </div>
        </div>
      )}
      {tree && tree.length > 0 && (
        <div className="tree">
          {tree.map((p) => (
            <NodeView key={p.code} node={p} depth={0} />
          ))}
        </div>
      )}
    </div>
  );
}
