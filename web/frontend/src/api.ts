// عميل API لواجهة المهندس — يستخدم بروكسي Vite أثناء التطوير ويمكن ضبط عنوان مخصص للإصدار EXE لاحقًا
const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? "";

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      if (body && body.detail) {
        detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
      }
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return (await res.json()) as T;
}

export interface TreeNode {
  code: string;
  name: string;
  type: "PROJECT" | "REGION" | "ZONE" | "LOCATION";
  status: string;
  source: string;
  review_status: string;
  regions?: TreeNode[];
  zones?: TreeNode[];
  locations?: TreeNode[];
}

export interface ImportRow {
  id: number;
  package_id: string;
  filename: string;
  status: string;
  device_id: string;
  counts: Record<string, number>;
  imported_at: string;
}

export interface ManualRow {
  id: number;
  title: string;
  manufacturer: string;
  model: string;
  equipment_kind: string;
  revision: string;
  status: string;
  uploaded_at: string;
  chunks: number;
}

export interface SearchHit {
  chunk_id: number;
  manual_id: number;
  manual_title: string;
  page: number;
  section: string;
  snippet: string;
  text: string;
  score: number;
}

export interface CloudStatus {
  configured: boolean;
  service_account_path: string | null;
}

export interface CloudPullResult {
  checked: number;
  processed: number;
  results: { file: string; status: string; detail?: string }[];
}

export interface ConflictRow {
  id: number;
  type: string;
  entity_type: string;
  code: string;
  incoming: unknown;
  existing: unknown;
  package: string;
  detected_at: string;
  status: string;
}

export interface VisitRow {
  visit_id: string;
  location_code: string;
  status: string;
  started_at: string;
}

export function countTree(tree: TreeNode[]): { projects: number; regions: number; zones: number; locations: number } {
  let projects = 0;
  let regions = 0;
  let zones = 0;
  let locations = 0;
  for (const p of tree) {
    projects += 1;
    for (const r of p.regions ?? []) {
      regions += 1;
      for (const z of r.zones ?? []) {
        zones += 1;
        locations += (z.locations ?? []).length;
      }
    }
  }
  return { projects, regions, zones, locations };
}
