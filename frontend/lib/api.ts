const BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000/api";

export class ApiError extends Error {
  constructor(public detail: string, public code: string, public status: number) {
    super(detail);
  }
}

export interface User {
  id: string;
  email: string;
  display_name: string;
  role: string;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: User;
}

const ACCESS_KEY = "sq_access";
const REFRESH_KEY = "sq_refresh";

/** Exchange the stored refresh token for a fresh access token (rotates the
 * refresh token too). Returns the new access token, or null if it can't. */
async function tryRefresh(): Promise<string | null> {
  if (typeof window === "undefined") return null;
  const rt = localStorage.getItem(REFRESH_KEY);
  if (!rt) return null;
  try {
    const resp = await fetch(`${BASE}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: rt }),
    });
    if (!resp.ok) return null;
    const data = await resp.json();
    localStorage.setItem(ACCESS_KEY, data.access_token);
    localStorage.setItem(REFRESH_KEY, data.refresh_token);
    return data.access_token as string;
  } catch {
    return null;
  }
}

export async function apiFetch<T>(
  path: string,
  opts: RequestInit = {},
  token?: string,
  _retried = false
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(opts.headers as Record<string, string>),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  let resp: Response;
  try {
    resp = await fetch(`${BASE}${path}`, { ...opts, headers });
  } catch {
    throw new ApiError("Cannot reach the server. Is the backend running?", "network_error", 0);
  }

  // Transparent token refresh: on a 401 (expired access token), use the refresh
  // token to mint a new one and retry the request once.
  if (resp.status === 401 && !_retried && !path.startsWith("/auth/")) {
    const fresh = await tryRefresh();
    if (fresh) return apiFetch<T>(path, opts, fresh, true);
  }

  if (!resp.ok) {
    const body = await resp.json().catch(() => ({ detail: "Request failed", code: "unknown" }));
    throw new ApiError(body.detail ?? "Request failed", body.code ?? "unknown", resp.status);
  }
  return resp.json() as Promise<T>;
}
