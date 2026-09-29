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

export interface CloudAutoStatus {
  enabled: boolean;
  interval_seconds: number;
  min_interval: number;
  max_interval: number;
  configured: boolean;
  last_run_at: string | null;
  last_result: { checked: number; processed: number } | null;
  last_error: string | null;
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
  visit_type: string;
  started_at: string;
  ended_at: string | null;
  status: string;
  package_id: string;
  imported_at: string;
}

export interface VisitEquipmentRow {
  kind: string;
  tag: string;
  model: string;
  running_hours: number | null;
  pressure_bar: number | null;
  status: string;
}

export interface VisitChecklistRow {
  item_code: string;
  status: string;
}

export interface VisitPhotoRow {
  id: number;
  target_type: string;
  target_ref: string;
  taken_at: string | null;
  lat: number | null;
  lon: number | null;
  url: string | null;
}

export interface VisitDetail {
  visit_id: string;
  location_code: string;
  visit_type: string;
  started_at: string;
  ended_at: string | null;
  status: string;
  equipment: VisitEquipmentRow[];
  checklist: VisitChecklistRow[];
  photos: VisitPhotoRow[];
}

export interface AssetHealthSummary {
  status: string;
  note: string | null;
  current_hours: number | null;
  hours_remaining: number | null;
  due_at_hours: number | null;
  rules_count: number;
  readings_count: number;
}

export interface AssetRow {
  asset_code: string;
  location_code: string;
  kind: string;
  tag: string;
  model: string | null;
  status: string;
  running_hours: number | null;
  running_hours_at: string | null;
  updated_at: string | null;
  health: AssetHealthSummary;
}

export interface AssetRuleEval {
  rule_id: number;
  maintenance_type: string | null;
  interval_hours?: number;
  interval_days?: number;
  description: string | null;
  manual_id: number | null;
  source_page: number | null;
  source_section: string | null;
  status: string;
  hours_remaining: number | null;
  due_at_hours?: number | null;
  note?: string;
}

export interface AssetReading {
  visit_id: string;
  at: string | null;
  hours: number | null;
  pressure_bar: number | null;
  status: string | null;
}

export interface AssetDetail {
  asset_code: string;
  location_code: string;
  kind: string;
  tag: string;
  model: string | null;
  status: string;
  running_hours: number | null;
  health: {
    status: string;
    note: string | null;
    baseline_hours: number | null;
    current_hours: number | null;
    hours_remaining: number | null;
    due_at_hours: number | null;
    rules_count: number;
    rules: AssetRuleEval[];
    readings_count: number;
    last_reading_at: string | null;
    readings: AssetReading[];
  };
}

export interface AlertRow {
  key: string;
  type: string;
  severity: "CRITICAL" | "WARNING" | "INFO";
  title: string;
  detail: string | null;
  asset_code: string | null;
  location_code: string | null;
  visit_id: string | null;
  ref: Record<string, unknown>;
  at: string | null;
}

export interface AlertsResponse {
  counts: { CRITICAL: number; WARNING: number; INFO: number };
  total: number;
  filtered: number;
  alerts: AlertRow[];
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
