const API_BASE = import.meta.env.REMOTE_API_BASE_URL || "/mongodhara/api";

function url(path: string): string {
  // Remove leading '/' if present, then base64url encode the path
  const pathWithoutLeadingSlash = path.startsWith("/") ? path.slice(1) : path;
  const encodedPath = btoa(pathWithoutLeadingSlash)
    .replace(/\+/g, '-')    // Replace + with -
    .replace(/\//g, '_')    // Replace / with _
    .replace(/=/g, '');     // Remove padding =
  return `${API_BASE}/${encodedPath}`;
  // return `${API_BASE}${path}`;
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

export async function apiUploadFile<T>(path: string, formData: FormData): Promise<T> {
  const res = await fetch(url(path), {
    method: "POST",
    body: formData,
  });
  if (!res.ok) throw new Error(`UPLOAD ${path} failed: ${res.status} ${res.statusText}`);
  return res.json();
}
