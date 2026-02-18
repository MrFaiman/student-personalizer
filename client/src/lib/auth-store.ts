import { create } from "zustand";
import { authApi, type UserResponse } from "./api/auth";

const AUTH_TOKEN_KEY = "auth_token";

interface AuthState {
  token: string | null;
  user: UserResponse | null;
  isAuthenticated: boolean;
  isInitialized: boolean;

  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  initialize: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  token: null,
  user: null,
  isAuthenticated: false,
  isInitialized: false,

  login: async (email: string, password: string) => {
    const { access_token } = await authApi.login(email, password);
    localStorage.setItem(AUTH_TOKEN_KEY, access_token);

    const user = await authApi.me(access_token);
    set({ token: access_token, user, isAuthenticated: true });
  },

  logout: () => {
    localStorage.removeItem(AUTH_TOKEN_KEY);
    set({ token: null, user: null, isAuthenticated: false });
    window.location.href = "/login";
  },

  initialize: async () => {
    if (get().isInitialized) return;

    const token = localStorage.getItem(AUTH_TOKEN_KEY);
    if (!token) {
      set({ isInitialized: true });
      return;
    }

    try {
      const user = await authApi.me(token);
      set({ token, user, isAuthenticated: true, isInitialized: true });
    } catch {
      localStorage.removeItem(AUTH_TOKEN_KEY);
      set({ isInitialized: true });
    }
  },
}));
