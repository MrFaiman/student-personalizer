import { create } from "zustand";
import { persist } from "zustand/middleware";
import { authApi } from "./api/auth";
import type { User, UserRole } from "./types/auth";

export interface MfaPending {
  mfaToken: string;
}

interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  user: User | null;
  isAuthenticated: boolean;
  mfaPending: MfaPending | null;

  login: (email: string, password: string) => Promise<void>;
  completeMfa: (code: string) => Promise<void>;
  logout: () => Promise<void>;
  refresh: () => Promise<boolean>;
  setTokens: (accessToken: string, refreshToken: string) => void;
  setUser: (user: User) => void;
  clearMfaPending: () => void;
  hasRole: (...roles: UserRole[]) => boolean;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      accessToken: null,
      refreshToken: null,
      user: null,
      isAuthenticated: false,
      mfaPending: null,

      login: async (email, password) => {
        const response = await authApi.login(email, password);
        if ("mfa_required" in response) {
          set({ mfaPending: { mfaToken: response.mfa_token } });
          return;
        }
        const user = await authApi.me(response.access_token);
        set({
          accessToken: response.access_token,
          refreshToken: response.refresh_token,
          user,
          isAuthenticated: true,
          mfaPending: null,
        });
      },

      completeMfa: async (code) => {
        const { mfaPending } = get();
        if (!mfaPending) throw new Error("No MFA challenge pending");
        const tokens = await authApi.mfaChallenge(mfaPending.mfaToken, code);
        const user = await authApi.me(tokens.access_token);
        set({
          accessToken: tokens.access_token,
          refreshToken: tokens.refresh_token,
          user,
          isAuthenticated: true,
          mfaPending: null,
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

      clearMfaPending: () => set({ mfaPending: null }),

      hasRole: (...roles) => {
        const { user } = get();
        return user ? roles.includes(user.role) : false;
      },
    }),
    {
      name: "auth",
      partialize: (s) => ({ accessToken: s.accessToken, refreshToken: s.refreshToken, user: s.user, isAuthenticated: s.isAuthenticated, mfaPending: s.mfaPending }),
    },
  ),
);
