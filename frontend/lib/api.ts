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

export async function apiFetch<T>(path: string, opts: RequestInit = {}, token?: string): Promise<T> {
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

  if (!resp.ok) {
    const body = await resp.json().catch(() => ({ detail: "Request failed", code: "unknown" }));
    throw new ApiError(body.detail ?? "Request failed", body.code ?? "unknown", resp.status);
  }
  return resp.json() as Promise<T>;
}
