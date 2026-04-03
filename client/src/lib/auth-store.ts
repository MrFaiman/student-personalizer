import { create } from "zustand";
import { persist } from "zustand/middleware";
import { authApi } from "./api/auth";
import type { User, UserRole } from "./types/auth";

/** One in-flight refresh: server rotates the refresh token, so concurrent POST /refresh races cause 401. */
let refreshInFlight: Promise<boolean> | null = null;

export interface MfaPending {
  mfaToken: string;
}

interface AuthState {
  accessToken: string | null;
  user: User | null;
  isAuthenticated: boolean;
  mfaPending: MfaPending | null;

  login: (email: string, password: string) => Promise<void>;
  completeMfa: (code: string) => Promise<void>;
  selectSchool: (schoolId: number) => Promise<void>;
  logout: () => Promise<void>;
  refresh: () => Promise<boolean>;
  setAccessToken: (accessToken: string) => void;
  setUser: (user: User) => void;
  clearMfaPending: () => void;
  hasRole: (...roles: UserRole[]) => boolean;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      accessToken: null,
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
          user,
          isAuthenticated: true,
          mfaPending: null,
        });
      },

      selectSchool: async (schoolId) => {
        const { accessToken } = get();
        if (!accessToken) throw new Error("Not authenticated");
        const tokens = await authApi.selectSchool(accessToken, schoolId);
        const user = await authApi.me(tokens.access_token);
        set({
          accessToken: tokens.access_token,
          user,
          isAuthenticated: true,
        });
      },

      logout: async () => {
        const { accessToken } = get();
        if (accessToken) {
          await authApi.logout(accessToken).catch(() => {});
        }
        set({ accessToken: null, user: null, isAuthenticated: false });
      },

      refresh: async () => {
        if (refreshInFlight) return refreshInFlight;
        refreshInFlight = (async () => {
          try {
            const tokens = await authApi.refresh();
            const user = await authApi.me(tokens.access_token);
            set({
              accessToken: tokens.access_token,
              user,
              isAuthenticated: true,
            });
            return true;
          } catch {
            set({ accessToken: null, user: null, isAuthenticated: false });
            return false;
          } finally {
            refreshInFlight = null;
          }
        })();
        return refreshInFlight;
      },

      setAccessToken: (accessToken) => set({ accessToken }),

      setUser: (user) => set({ user }),

      clearMfaPending: () => set({ mfaPending: null }),

      hasRole: (...roles) => {
        const { user } = get();
        return user ? roles.includes(user.role) : false;
      },
    }),
    {
      // New storage key so older persisted blobs (with JWTs in localStorage) are not rehydrated.
      name: "sp_auth_v2",
      version: 1,
      partialize: (s) => ({
        user: s.user,
        isAuthenticated: s.isAuthenticated,
        mfaPending: s.mfaPending,
      }),
    },
  ),
);
