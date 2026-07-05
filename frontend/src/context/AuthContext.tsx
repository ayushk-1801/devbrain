import { createContext, useContext, useEffect, useState, ReactNode } from 'react';

export const PLATFORM_API = 'http://localhost:9000';
const TOKEN_KEY = 'devbrain_token';
const DEPLOYED_URL = (import.meta.env.VITE_DEPLOYED_URL || '').replace(/\/+$/, '');

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
  const [showDeployModal, setShowDeployModal] = useState(false);

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
    if (DEPLOYED_URL && window.location.origin === DEPLOYED_URL) {
      setShowDeployModal(true);
      return;
    }
    window.location.href = `${PLATFORM_API}/auth/github/login`;
  };

  const logout = () => {
    localStorage.removeItem(TOKEN_KEY);
    setUser(null);
    setToken(null);
    window.location.href = '/';
  };

  return (
    <>
      {showDeployModal && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm px-4">
          <div className="bg-bg-card rounded-2xl border border-border-soft p-8 max-w-md w-full shadow-2xl">
            <h3 className="font-display font-bold text-lg text-text-primary">Infrastructure Not Ready</h3>
            <p className="text-text-muted text-sm mt-3 leading-relaxed">
              The hosted version of DevBrain is not ready yet. You can self-host it
              on your own infrastructure to get started right away.
            </p>
            <div className="flex items-center gap-3 mt-6">
              <button
                onClick={() => setShowDeployModal(false)}
                className="px-5 py-2.5 rounded-xl border border-border-soft text-text-primary text-sm font-medium cursor-pointer hover:bg-bg-secondary transition-colors"
              >
                Cancel
              </button>
              <a
                href="/docs"
                onClick={() => setShowDeployModal(false)}
                className="px-5 py-2.5 rounded-xl bg-btn-dark text-btn-dark-text text-sm font-medium cursor-pointer hover:bg-btn-dark-hover transition-colors text-center no-underline"
              >
                Self-Host
              </a>
            </div>
          </div>
        </div>
      )}
      <AuthContext.Provider value={{ user, token, isLoading, login, logout }}>
        {children}
      </AuthContext.Provider>
    </>
  );
}

export const useAuth = () => useContext(AuthContext);
