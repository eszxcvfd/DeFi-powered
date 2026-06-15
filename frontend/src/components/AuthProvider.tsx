import { createContext, useCallback, useContext, useEffect, useState } from "react";
import type { ReactNode } from "react";
import { useLocation } from "react-router-dom";
import { getAuthBootstrap, login as loginApi, logout as logoutApi } from "@/api/auth";
import type { AuthSession, LoginRequest } from "@/types/auth";

interface AuthContextValue {
  loading: boolean;
  session: AuthSession | null;
  signIn: (payload: LoginRequest) => Promise<AuthSession>;
  signOut: () => Promise<void>;
  refresh: () => Promise<AuthSession | null>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<AuthSession | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const location = useLocation();

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    getAuthBootstrap()
      .then((b) => {
        if (cancelled) return;
        setSession(b.session ?? null);
      })
      .catch(() => undefined)
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [location.pathname]);

  const signIn = useCallback(async (payload: LoginRequest) => {
    const { session: s } = await loginApi(payload);
    setSession(s);
    return s;
  }, []);

  const signOut = useCallback(async () => {
    try {
      await logoutApi();
    } finally {
      setSession(null);
    }
  }, []);

  const refresh = useCallback(async () => {
    try {
      const { refreshSession } = await import("@/api/auth");
      const next = await refreshSession();
      setSession(next);
      return next;
    } catch {
      setSession(null);
      return null;
    }
  }, []);

  return (
    <AuthContext.Provider value={{ loading, session, signIn, signOut, refresh }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used inside an AuthProvider");
  }
  return ctx;
}
