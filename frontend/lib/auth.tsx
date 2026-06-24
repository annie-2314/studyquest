"use client";
import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { apiFetch, AuthResponse, User } from "./api";

interface AuthState {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string, display_name: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);
const ACCESS_KEY = "sq_access";
const REFRESH_KEY = "sq_refresh";

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const loadMe = useCallback(async () => {
    const token = localStorage.getItem(ACCESS_KEY);
    if (!token) {
      setLoading(false);
      return;
    }
    try {
      const me = await apiFetch<User>("/auth/me", {}, token);
      setUser(me);
    } catch {
      localStorage.removeItem(ACCESS_KEY);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadMe();
  }, [loadMe]);

  function persist(res: AuthResponse) {
    localStorage.setItem(ACCESS_KEY, res.access_token);
    localStorage.setItem(REFRESH_KEY, res.refresh_token);
    setUser(res.user);
  }

  const login = async (email: string, password: string) => {
    persist(
      await apiFetch<AuthResponse>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      })
    );
  };

  const signup = async (email: string, password: string, display_name: string) => {
    persist(
      await apiFetch<AuthResponse>("/auth/signup", {
        method: "POST",
        body: JSON.stringify({ email, password, display_name }),
      })
    );
  };

  const logout = () => {
    const rt = localStorage.getItem(REFRESH_KEY);
    if (rt) {
      apiFetch("/auth/logout", { method: "POST", body: JSON.stringify({ refresh_token: rt }) }).catch(
        () => {}
      );
    }
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, signup, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
