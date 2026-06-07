// FORK: multi-tenancy — Auth context
import React, { createContext, useCallback, useContext, useEffect, useState } from "react";
import { getAPIURL } from "../../utils/url";

export interface User {
  id: number;
  email: string;
  name: string;
  avatar_url: string | null;
  is_admin: boolean;
}

export interface AuthProvider {
  name: string;
  display_name: string;
}

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  authEnabled: boolean;
  providers: AuthProvider[];
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue>({
  user: null,
  loading: true,
  authEnabled: false,
  providers: [],
  logout: async () => {},
  refresh: async () => {},
});

export const AuthProvider = ({ children }: { children: React.ReactNode }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [authEnabled, setAuthEnabled] = useState(false);
  const [providers, setProviders] = useState<AuthProvider[]>([]);

  const refresh = useCallback(async () => {
    try {
      const providersResp = await fetch(`${getAPIURL()}/auth/providers`);
      const providersList: AuthProvider[] = await providersResp.json();
      setProviders(providersList);
      setAuthEnabled(providersList.length > 0);

      if (providersList.length > 0) {
        const meResp = await fetch(`${getAPIURL()}/auth/me`, { credentials: "include" });
        if (meResp.ok) {
          const data: User = await meResp.json();
          setUser(data);
        } else {
          setUser(null);
        }
      }
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const logout = useCallback(async () => {
    await fetch(`${getAPIURL()}/auth/logout`, { method: "POST", credentials: "include" });
    setUser(null);
    window.location.href = "/login";
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, authEnabled, providers, logout, refresh }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
