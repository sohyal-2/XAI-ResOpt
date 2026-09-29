"use client";

import { createContext, useContext, useEffect, useState } from "react";

import { fetchCurrentUser, login as loginRequest, logout as logoutRequest, signup as signupRequest } from "@/lib/api";
import type { AuthResponse, User } from "@/types/auth";

const TOKEN_KEY = "xai-resopt.access-token";

interface AuthContextValue {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, fullName: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  clearError: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

function persistSession(response: AuthResponse): void {
  sessionStorage.setItem(TOKEN_KEY, response.access_token);
  localStorage.setItem("access_token", response.access_token);
}

export function AuthProvider({ children }: Readonly<{ children: React.ReactNode }>) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const storedToken = sessionStorage.getItem(TOKEN_KEY) || localStorage.getItem("access_token");
    if (!storedToken) {
      setIsLoading(false);
      return;
    }
    setToken(storedToken);
    fetchCurrentUser(storedToken)
      .then(setUser)
      .catch(() => {
        sessionStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem("access_token");
        setToken(null);
        setUser(null);
      })
      .finally(() => setIsLoading(false));
  }, []);

  async function authenticate(request: () => Promise<AuthResponse>): Promise<void> {
    setIsLoading(true);
    setError(null);
    try {
      const response = await request();
      persistSession(response);
      setToken(response.access_token);
      setUser(response.user);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Authentication failed.");
      throw requestError;
    } finally {
      setIsLoading(false);
    }
  }

  async function logout(): Promise<void> {
    const currentToken = token;
    setError(null);
    try {
      if (currentToken) await logoutRequest(currentToken);
    } catch {
      // The local session is still cleared when the server session has expired.
    } finally {
      sessionStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem("access_token");
      setToken(null);
      setUser(null);
    }
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isLoading,
        error,
        login: (email, password) => authenticate(() => loginRequest(email, password)),
        signup: (email, fullName, password) => authenticate(() => signupRequest(email, fullName, password)),
        logout,
        clearError: () => setError(null),
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider.");
  return context;
}