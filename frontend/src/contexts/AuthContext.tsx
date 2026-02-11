"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import {
  storeTokens,
  clearTokens,
  getStoredToken,
} from "@/lib/api/client";
import { login as apiLogin, register as apiRegister } from "@/lib/api/auth";

const USERNAME_KEY = "git_dash_username";

interface AuthState {
  isAuthenticated: boolean;
  isLoading: boolean;
  username: string | null;
}

interface AuthContextValue extends AuthState {
  login: (username: string, password: string) => Promise<void>;
  register: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({
    isAuthenticated: false,
    isLoading: true,
    username: null,
  });

  // Check for existing token on mount
  useEffect(() => {
    const token = getStoredToken();
    if (token) {
      const storedUsername = localStorage.getItem(USERNAME_KEY);
      setState({
        isAuthenticated: true,
        isLoading: false,
        username: storedUsername,
      });
    } else {
      setState({ isAuthenticated: false, isLoading: false, username: null });
    }
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    const res = await apiLogin(username, password);
    storeTokens(res.access_token, res.refresh_token);
    localStorage.setItem(USERNAME_KEY, username);
    setState({ isAuthenticated: true, isLoading: false, username });
  }, []);

  const register = useCallback(async (username: string, password: string) => {
    const res = await apiRegister(username, password);
    storeTokens(res.access_token, res.refresh_token);
    const name = res.user.github_login;
    localStorage.setItem(USERNAME_KEY, name);
    setState({
      isAuthenticated: true,
      isLoading: false,
      username: name,
    });
  }, []);

  const logout = useCallback(() => {
    clearTokens();
    localStorage.removeItem(USERNAME_KEY);
    setState({ isAuthenticated: false, isLoading: false, username: null });
  }, []);

  return (
    <AuthContext.Provider value={{ ...state, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
