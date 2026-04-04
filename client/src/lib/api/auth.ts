import {
  AccessTokenResponseSchema,
  LoginResponseSchema,
  MfaBackupCodesResponseSchema,
  MfaSetupResponseSchema,
  SchoolOptionsSchema,
  SsoStatusSchema,
  UserSchema,
  type AccessTokenResponse,
  type LoginResponse,
  type MfaBackupCodesResponse,
  type MfaSetupResponse,
  type SchoolOption,
  type SsoStatus,
  type User,
} from "../types/auth";
import { API_BASE_URL } from "./base-url";

const cred: RequestCredentials = "include";

async function post<T>(
  endpoint: string,
  body: unknown,
  schema: { parse: (v: unknown) => T },
): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${endpoint}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    credentials: cred,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? `HTTP ${res.status}`);
  }
  return schema.parse(await res.json());
}

async function get<T>(
  endpoint: string,
  token: string,
  schema: { parse: (v: unknown) => T },
): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${endpoint}`, {
    headers: { Authorization: `Bearer ${token}` },
    credentials: cred,
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return schema.parse(await res.json());
}

async function authPost<T>(
  endpoint: string,
  token: string,
  body: unknown,
  schema: { parse: (v: unknown) => T },
): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${endpoint}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify(body),
    credentials: cred,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? `HTTP ${res.status}`);
  }
  return schema.parse(await res.json());
}

export const authApi = {
  login: (email: string, password: string): Promise<LoginResponse> =>
    post("/api/auth/login", { email, password }, LoginResponseSchema),

  mfaChallenge: (mfa_token: string, code: string): Promise<AccessTokenResponse> =>
    post("/api/auth/mfa/challenge", { mfa_token, code }, AccessTokenResponseSchema),

  mfaSetup: (token: string): Promise<MfaSetupResponse> =>
    authPost("/api/auth/mfa/setup", token, {}, MfaSetupResponseSchema),

  mfaVerify: (token: string, code: string): Promise<MfaBackupCodesResponse> =>
    authPost("/api/auth/mfa/verify", token, { code }, MfaBackupCodesResponseSchema),

  mfaDisable: (token: string, code: string): Promise<void> =>
    authPost("/api/auth/mfa/disable", token, { code }, { parse: () => undefined }),

  refresh: (): Promise<AccessTokenResponse> =>
    post("/api/auth/refresh", {}, AccessTokenResponseSchema),

  logout: async (access_token: string): Promise<void> => {
    await fetch(`${API_BASE_URL}/api/auth/logout`, {
      method: "POST",
      headers: { Authorization: `Bearer ${access_token}` },
      credentials: cred,
    });
  },

  me: (token: string): Promise<User> => get("/api/auth/me", token, UserSchema),

  schools: async (): Promise<SchoolOption[]> => {
    const res = await fetch(`${API_BASE_URL}/api/auth/schools`);
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail ?? `HTTP ${res.status}`);
    }
    return SchoolOptionsSchema.parse(await res.json());
  },

  mySchools: (token: string): Promise<SchoolOption[]> =>
    get("/api/auth/my-schools", token, SchoolOptionsSchema),

  selectSchool: (token: string, school_id: number): Promise<AccessTokenResponse> =>
    authPost("/api/auth/select-school", token, { school_id }, AccessTokenResponseSchema),

  ssoComplete: (code: string): Promise<AccessTokenResponse> =>
    post("/api/auth/sso/complete", { code }, AccessTokenResponseSchema),

  ssoStatus: async (): Promise<SsoStatus> => {
    const res = await fetch(`${API_BASE_URL}/api/auth/sso/status`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return SsoStatusSchema.parse(await res.json());
  },

  changePassword: async (
    token: string,
    current_password: string,
    new_password: string,
  ): Promise<void> => {
    const res = await fetch(`${API_BASE_URL}/api/auth/change-password`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ current_password, new_password }),
      credentials: cred,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      const detail = err.detail;
      const message =
        typeof detail === "string"
          ? detail
          : detail !== undefined && detail !== null
            ? JSON.stringify(detail)
            : `HTTP ${res.status}`;
      throw new Error(message);
    }
  },
};
