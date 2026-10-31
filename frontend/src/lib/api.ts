export class ApiError extends Error {
  code: string;
  status: number;
  details: unknown;

  constructor(message: string, code: string, status: number, details: unknown = {}) {
    super(message);
    this.code = code;
    this.status = status;
    this.details = details;
  }
}

function csrfToken(): string {
  const match = document.cookie.match(/(?:^|;\s*)apaar_csrf=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : "";
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (!(init.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  const token = csrfToken();
  if (token) headers.set("X-CSRF-Token", token);

  const response = await fetch(`/api/v1${path}`, {
    ...init,
    headers,
    credentials: "include",
  });

  const contentType = response.headers.get("content-type") || "";
  if (!response.ok) {
    let payload: { error?: { code?: string; message?: string; details?: unknown }; detail?: string } = {};
    if (contentType.includes("application/json")) {
      payload = await response.json().catch(() => ({}));
    }
    throw new ApiError(
      payload.error?.message || payload.detail || `Request failed (${response.status})`,
      payload.error?.code || `HTTP_${response.status}`,
      response.status,
      payload.error?.details ?? {},
    );
  }
  if (response.status === 204) return undefined as T;
  if (!contentType.includes("application/json")) {
    return (await response.text()) as unknown as T;
  }
  return (await response.json()) as T;
}

export async function apiBlob(path: string): Promise<Blob> {
  const response = await fetch(`/api/v1${path}`, { credentials: "include" });
  if (!response.ok) throw new ApiError("Download failed", `HTTP_${response.status}`, response.status);
  return response.blob();
}

export function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}
