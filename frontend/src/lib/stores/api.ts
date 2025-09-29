import { triggerAuthError } from './error-overlay';

const API_BASE = import.meta.env.VITE_API_BASE || "/mdhara/api/v1";

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
  
  // Handle different HTTP status codes
  if (res.status === 401) {
    triggerAuthError(res.status, `Authentication failed for ${path}`);
    throw new Error(`Auth error: ${res.status}`);
  }
  
  // Parse JSON once for both success and error cases
  const data = await res.json();
  
  if (!res.ok) {
    const errorMessage = data.detail || `GET ${path} failed: ${res.status} ${res.statusText}`;
    throw new Error(errorMessage);
  }
  
  return data;
}

export async function apiPost<T>(path: string, body?: any): Promise<T> {
  const res = await fetch(url(path), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  
  // Handle different HTTP status codes
  if (res.status === 401) {
    triggerAuthError(res.status, `Authentication failed for ${path}`);
    throw new Error(`Auth error: ${res.status}`);
  }
  
  // Parse JSON once for both success and error cases
  const data = await res.json();
  
  if (!res.ok) {
    const errorMessage = data.detail || `POST ${path} failed: ${res.status} ${res.statusText}`;
    throw new Error(errorMessage);
  }
  
  return data;
}

export async function apiPut<T>(path: string, body: any): Promise<T> {
  const res = await fetch(url(path), {
    method: "PUT",  
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  
  // Handle different HTTP status codes
  if (res.status === 401) {
    triggerAuthError(res.status, `Authentication failed for ${path}`);
    throw new Error(`Auth error: ${res.status}`);
  }
  
  // Parse JSON once for both success and error cases
  const data = await res.json();
  
  if (!res.ok) {
    const errorMessage = data.detail || `PUT ${path} failed: ${res.status} ${res.statusText}`;
    throw new Error(errorMessage);
  }
  
  return data;
}

export async function apiDelete<T>(path: string): Promise<T> {
  const res = await fetch(url(path), {
    method: "DELETE",
  });
  
  // Handle different HTTP status codes
  if (res.status === 401) {
    triggerAuthError(res.status, `Authentication failed for ${path}`);
    throw new Error(`Auth error: ${res.status}`);
  }
  
  // Parse JSON once for both success and error cases
  const data = await res.json();
  
  if (!res.ok) {
    const errorMessage = data.detail || `DELETE ${path} failed: ${res.status} ${res.statusText}`;
    throw new Error(errorMessage);
  }

  return data;
}

export async function apiUploadFile<T>(path: string, formData: FormData): Promise<T> {
  const res = await fetch(url(path), {
    method: "POST",
    body: formData,
  });
  
  // Handle different HTTP status codes
  if (res.status === 401) {
    triggerAuthError(res.status, `Authentication failed for ${path}`);
    throw new Error(`Auth error: ${res.status}`);
  }
  
  // Parse JSON once for both success and error cases
  const data = await res.json();
  
  if (!res.ok) {
    const errorMessage = data.detail || `UPLOAD ${path} failed: ${res.status} ${res.statusText}`;
    throw new Error(errorMessage);
  }
  
  return data;
}

export async function apiDownload(path: string): Promise<Blob> {
  const res = await fetch(url(path));
  
  // Handle different HTTP status codes
  if (res.status === 401) {
    triggerAuthError(res.status, `Authentication failed for ${path}`);
    throw new Error(`Auth error: ${res.status}`);
  }
  
  if (!res.ok) {
    // Parse JSON error response to extract server message
    const errorData = await res.json();
    const errorMessage = errorData.detail || `DOWNLOAD ${path} failed: ${res.status} ${res.statusText}`;
    throw new Error(errorMessage);
  }
  
  return res.blob();
}

export async function apiDownloadText(path: string): Promise<string> {
  const res = await fetch(url(path));
  
  // Handle different HTTP status codes
  if (res.status === 401) {
    triggerAuthError(res.status, `Authentication failed for ${path}`);
    throw new Error(`Auth error: ${res.status}`);
  }
  
  if (!res.ok) {
    // Parse JSON error response to extract server message
    const errorData = await res.json();
    const errorMessage = errorData.detail || `DOWNLOAD ${path} failed: ${res.status} ${res.statusText}`;
    throw new Error(errorMessage);
  }
  
  return res.text();
}