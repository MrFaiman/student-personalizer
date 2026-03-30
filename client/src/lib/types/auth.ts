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
});
export type User = z.infer<typeof UserSchema>;

export const TokenResponseSchema = z.object({
  access_token: z.string(),
  refresh_token: z.string(),
  token_type: z.string().default("bearer"),
});
export type TokenResponse = z.infer<typeof TokenResponseSchema>;
