import { createContext, useContext, useEffect, useState, ReactNode } from 'react';

export const PLATFORM_API = 'http://localhost:9000';
const TOKEN_KEY = 'devbrain_token';

interface User {
  id: number;
  login: string;
  avatar_url: string;
}

interface AuthContextValue {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  login: () => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue>(null!);

function decodeJWT(token: string): Record<string, unknown> | null {
  try {
    const parts = token.split('.');
    if (parts.length !== 3) return null;
    // base64url → base64
    const base64 = parts[1].replace(/-/g, '+').replace(/_/g, '/');
    const padded = base64.padEnd(base64.length + (4 - (base64.length % 4)) % 4, '=');
    const payload = JSON.parse(atob(padded));
    return payload;
  } catch {
    return null;
  }
}

function isTokenValid(token: string): { valid: boolean; payload: Record<string, unknown> | null } {
  const payload = decodeJWT(token);
  if (!payload) return { valid: false, payload: null };
  const exp = payload.exp as number | undefined;
  const nowSeconds = Math.floor(Date.now() / 1000);
  if (exp && exp < nowSeconds) return { valid: false, payload: null };
  return { valid: true, payload };
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Step 1: Check URL for ?token=... query param
    const params = new URLSearchParams(window.location.search);
    const urlToken = params.get('token');

    let activeToken: string | null = null;

    if (urlToken) {
      localStorage.setItem(TOKEN_KEY, urlToken);
      activeToken = urlToken;
      // Remove token from URL without triggering a reload
      const newUrl = new URL(window.location.href);
      newUrl.searchParams.delete('token');
      window.history.replaceState({}, '', newUrl.pathname + (newUrl.search !== '?' ? newUrl.search : '') + newUrl.hash);
    } else {
      activeToken = localStorage.getItem(TOKEN_KEY);
    }

    // Step 2: Validate token and decode user
    if (activeToken) {
      const { valid, payload } = isTokenValid(activeToken);
      if (valid && payload) {
        setToken(activeToken);
        setUser({
          id: Number((payload as any).sub ?? payload.id),
          login: payload.login,
          avatar_url: (payload as any).avatar ?? payload.avatar_url,
        });
      } else {
        // Token expired or invalid — clear it
        localStorage.removeItem(TOKEN_KEY);
      }
    }

    setIsLoading(false);
  }, []);

  const login = () => {
    window.location.href = `${PLATFORM_API}/auth/github/login`;
  };

  const logout = () => {
    localStorage.removeItem(TOKEN_KEY);
    setUser(null);
    setToken(null);
    window.location.href = '/';
  };

  return (
    <AuthContext.Provider value={{ user, token, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
