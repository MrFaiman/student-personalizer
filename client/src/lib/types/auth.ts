import { z } from "zod";

export const UserRoleSchema = z.enum(["admin", "teacher", "viewer"]);
export type UserRole = z.infer<typeof UserRoleSchema>;

export const UserSchema = z.object({
  id: z.string(),
  email: z.string(),
  display_name: z.string(),
  role: UserRoleSchema,
  is_active: z.boolean(),
  must_change_password: z.boolean(),
  mfa_enabled: z.boolean().default(false),
  mfa_verified: z.boolean().default(false),
  identity_provider: z.string().default("local"),
  school_id: z.number().int().nullable().default(null),
  school_name: z.string().nullable().default(null),
});
export type User = z.infer<typeof UserSchema>;

export const TokenResponseSchema = z.object({
  access_token: z.string(),
  refresh_token: z.string(),
  token_type: z.string().default("bearer"),
});
export type TokenResponse = z.infer<typeof TokenResponseSchema>;

export const MfaChallengeResponseSchema = z.object({
  mfa_required: z.literal(true),
  mfa_token: z.string(),
});
export type MfaChallengeResponse = z.infer<typeof MfaChallengeResponseSchema>;

export const MfaSetupResponseSchema = z.object({
  provisioning_uri: z.string(),
  secret: z.string(),
});
export type MfaSetupResponse = z.infer<typeof MfaSetupResponseSchema>;

export const MfaBackupCodesResponseSchema = z.object({
  backup_codes: z.array(z.string()),
});
export type MfaBackupCodesResponse = z.infer<typeof MfaBackupCodesResponseSchema>;

export const LoginResponseSchema = z.union([
  MfaChallengeResponseSchema,
  TokenResponseSchema,
]);
export type LoginResponse = z.infer<typeof LoginResponseSchema>;

export const SsoStatusSchema = z.object({
  sso_enabled: z.boolean(),
});
export type SsoStatus = z.infer<typeof SsoStatusSchema>;

export const SchoolOptionSchema = z.object({
  school_id: z.number().int(),
  school_name: z.string(),
});
export const SchoolOptionsSchema = z.array(SchoolOptionSchema);
export type SchoolOption = z.infer<typeof SchoolOptionSchema>;

export const UsersSchema = z.array(UserSchema);
export type Users = z.infer<typeof UsersSchema>;
