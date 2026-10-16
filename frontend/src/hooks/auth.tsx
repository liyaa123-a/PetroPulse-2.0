import { createContext, ReactNode, useCallback, useContext, useEffect, useState } from "react";
import { api, getToken, setToken } from "../api/client";
import type { User } from "../types";

interface Ctx { user: User | null; ready: boolean; login(e: string, p: string): Promise<void>; register(e: string, n: string, p: string): Promise<void>; logout(): Promise<void>; refresh(): Promise<void> }
const AuthCtx = createContext<Ctx>(null as any);
export const useAuth = () => useContext(AuthCtx);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);
  const refresh = useCallback(async () => { try { setUser((await api.get<User>("/auth/me")).data); } catch { setToken(null); setUser(null); } }, []);
  useEffect(() => { (getToken() ? refresh() : Promise.resolve()).finally(() => setReady(true)); }, [refresh]);
  useEffect(() => { const h = () => setUser(null); window.addEventListener("pp-auth-expired", h); return () => window.removeEventListener("pp-auth-expired", h); }, []);
  const enter = (d: { token: string; user: User }) => { setToken(d.token); setUser(d.user); };
  const value: Ctx = {
    user, ready, refresh,
    login: async (email, password) => enter((await api.post("/auth/login", { email, password })).data),
    register: async (email, full_name, password) => enter((await api.post("/auth/register", { email, full_name, password })).data),
    logout: async () => { try { await api.post("/auth/logout"); } catch { /* token may already be invalid */ } setToken(null); setUser(null); },
  };
  return <AuthCtx.Provider value={value}>{children}</AuthCtx.Provider>;
}
