// Central API client. Base URL comes from VITE_API_BASE_URL - never hard-coded.
const BASE = ((import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "").replace(/\/+$/, "");
export const apiConfigured = BASE !== "";
const KEY = "pp_token";

export class ApiError extends Error {
  status: number; code: string; fields?: Record<string, string>;
  constructor(status: number, code: string, message: string, fields?: Record<string, string>) { super(message); this.status = status; this.code = code; this.fields = fields; }
}

function jwtExp(t: string): number { try { return JSON.parse(atob(t.split(".")[1].replace(/-/g, "+").replace(/_/g, "/"))).exp * 1000; } catch { return 0; } }
let token: string | null = null;
try { const raw = sessionStorage.getItem(KEY); if (raw && jwtExp(raw) > Date.now()) token = raw; } catch { /* storage unavailable */ }
export const getToken = () => token;
export function setToken(t: string | null) {
  token = t;
  try { t ? sessionStorage.setItem(KEY, t) : sessionStorage.removeItem(KEY); } catch { /* ignore */ }
}

export function qs(params: Record<string, unknown>): string {
  const p = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => { if (v !== undefined && v !== null && v !== "") p.set(k, String(v)); });
  const s = p.toString();
  return s ? "?" + s : "";
}

async function raw(method: string, path: string, body?: unknown): Promise<Response> {
  if (!apiConfigured) throw new ApiError(0, "NOT_CONFIGURED", "The API address is not configured. Set VITE_API_BASE_URL and rebuild.");
  let res: Response;
  try {
    res = await fetch(BASE + "/api" + path, {
      method, headers: { ...(body !== undefined ? { "Content-Type": "application/json" } : {}), ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch { throw new ApiError(0, "NETWORK", "Cannot reach the server. If it was idle it may be waking up - wait a few seconds and retry."); }
  if (!res.ok) {
    let e: any = {}; try { e = (await res.json()).error ?? {}; } catch { /* non-JSON error */ }
    if (res.status === 401 && token && path !== "/auth/login") { setToken(null); window.dispatchEvent(new Event("pp-auth-expired")); }
    throw new ApiError(res.status, e.code ?? "ERROR", e.message ?? `Request failed (${res.status})`, e.fields);
  }
  return res;
}

export type Result<T> = { data: T; meta?: any };
const json = async <T,>(r: Response) => (await r.json()) as Result<T>;
export const api = {
  get: <T = any,>(p: string) => raw("GET", p).then(json<T>),
  post: <T = any,>(p: string, b?: unknown) => raw("POST", p, b ?? {}).then(json<T>),
  put: <T = any,>(p: string, b: unknown) => raw("PUT", p, b).then(json<T>),
  patch: <T = any,>(p: string, b: unknown) => raw("PATCH", p, b).then(json<T>),
  del: <T = any,>(p: string, b?: unknown) => raw("DELETE", p, b).then(json<T>),
  async download(path: string, filename: string) {
    const blob = await (await raw("GET", path)).blob();
    const url = URL.createObjectURL(blob), a = document.createElement("a");
    a.href = url; a.download = filename; document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
  },
};
