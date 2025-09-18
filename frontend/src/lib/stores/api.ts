const API_BASE = import.meta.env.REMOTE_API_BASE_URL || "/mongodharaapi";

function url(path: string): string {
  return `${API_BASE}${path.startsWith("/") ? path : "/" + path}`;
}

export async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(url(path));
  if (!res.ok) throw new Error(`GET ${path} failed: ${res.status} ${res.statusText}`);
  return res.json();
}

export async function apiPost<T>(path: string, body?: any): Promise<T> {
  const res = await fetch(url(path), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`POST ${path} failed: ${res.status} ${res.statusText}`);
  return res.json();
}

export async function apiPut<T>(path: string, body: any): Promise<T> {
  const res = await fetch(url(path), {
    method: "PUT",  
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`PUT ${path} failed: ${res.status} ${res.statusText}`);
  return res.json();
}

export async function apiDelete<T>(path: string): Promise<T> {
  const res = await fetch(url(path), {
    method: "DELETE",
  });
  if (!res.ok) throw new Error(`DELETE ${path} failed: ${res.status} ${res.statusText}`);
  return res.json();
}
