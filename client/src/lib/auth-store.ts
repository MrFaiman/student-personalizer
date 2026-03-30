import { create } from "zustand";
import { persist } from "zustand/middleware";
import { authApi } from "./api/auth";
import type { User, UserRole } from "./types/auth";

interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  user: User | null;
  isAuthenticated: boolean;

  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refresh: () => Promise<boolean>;
  setTokens: (accessToken: string, refreshToken: string) => void;
  setUser: (user: User) => void;
  hasRole: (...roles: UserRole[]) => boolean;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      accessToken: null,
      refreshToken: null,
      user: null,
      isAuthenticated: false,

      login: async (email, password) => {
        const tokens = await authApi.login(email, password);
        const user = await authApi.me(tokens.access_token);
        set({
          accessToken: tokens.access_token,
          refreshToken: tokens.refresh_token,
          user,
          isAuthenticated: true,
        });
      },

      logout: async () => {
        const { accessToken } = get();
        if (accessToken) {
          await authApi.logout(accessToken).catch(() => {});
        }
        set({ accessToken: null, refreshToken: null, user: null, isAuthenticated: false });
      },

      refresh: async () => {
        const { refreshToken } = get();
        if (!refreshToken) return false;
        try {
          const tokens = await authApi.refresh(refreshToken);
          const user = await authApi.me(tokens.access_token);
          set({
            accessToken: tokens.access_token,
            refreshToken: tokens.refresh_token,
            user,
            isAuthenticated: true,
          });
          return true;
        } catch {
          set({ accessToken: null, refreshToken: null, user: null, isAuthenticated: false });
          return false;
        }
      },

      setTokens: (accessToken, refreshToken) => set({ accessToken, refreshToken }),

      setUser: (user) => set({ user }),

      hasRole: (...roles) => {
        const { user } = get();
        return user ? roles.includes(user.role) : false;
      },
    }),
    {
      name: "auth",
      partialize: (s) => ({ accessToken: s.accessToken, refreshToken: s.refreshToken, user: s.user, isAuthenticated: s.isAuthenticated }),
    },
  ),
);
