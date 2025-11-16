export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`GET ${path} -> ${res.status}`);
  return res.json() as Promise<T>;
}

export async function apiPost<T>(path: string, body?: any): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(`POST ${path} -> ${res.status}`);
  return res.json() as Promise<T>;
}

export async function apiPut<T>(path: string, body?: any): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(`PUT ${path} -> ${res.status}`);
  return res.json() as Promise<T>;
}

// Helpers usados por páginas existentes
export async function getHealth(): Promise<any> {
  return apiGet<any>("/healthz");
}

export async function getEstoque(
  page = 1,
  size = 50,
  sort_by = "created_at",
  sort_dir = "desc",
  search = "",
  origem = "",
  status = ""
): Promise<{ items: any[]; page: number; size: number; total: number; total_pages: number }> {
  const params = new URLSearchParams({
    page: String(page),
    size: String(size),
    sort_by,
    sort_dir,
    ...(search && { search }),
    ...(origem && { origem }),
    ...(status && { status }),
  });
  return apiGet(`/estoque?${params.toString()}`);
}