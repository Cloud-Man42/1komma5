"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import {
  AuthUser,
  fetchCurrentUser,
  hasBreakGlassToken,
  hasPermission,
  login as loginRequest,
  logout as logoutRequest,
} from "@/lib/auth";
import { setAdminToken } from "@/lib/adminAuth";

interface AuthContextValue {
  user: AuthUser | null;
  loading: boolean;
  isAuthenticated: boolean;
  login: (usernameOrEmail: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
  can: (permission: string) => boolean;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const me = await fetchCurrentUser();
      if (me) {
        setUser(me);
        setLoading(false);
        return;
      }
    } catch {
      // fall through to break-glass / anonymous
    }
    if (hasBreakGlassToken()) {
      setUser({
        id: null,
        username: "break-glass",
        email: "",
        displayName: "Break-glass Admin",
        roles: ["SUPER_ADMIN"],
        permissions: ["*"],
        sites: [],
        mustChangePassword: false,
        authMethod: "break_glass",
      });
    } else {
      setUser(null);
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const login = useCallback(async (usernameOrEmail: string, password: string) => {
    const me = await loginRequest(usernameOrEmail, password);
    setAdminToken("");
    setUser(me);
  }, []);

  const logout = useCallback(async () => {
    if (user?.authMethod === "break_glass") {
      setAdminToken("");
      setUser(null);
      window.location.href = "/login";
      return;
    }
    try {
      await logoutRequest();
    } finally {
      setAdminToken("");
      setUser(null);
      window.location.href = "/login";
    }
  }, [user?.authMethod]);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      loading,
      isAuthenticated: user !== null,
      login,
      logout,
      refresh,
      can: (permission: string) => hasPermission(user, permission),
    }),
    [user, loading, login, logout, refresh],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
