import { z } from "zod";
import { fetchApi } from "./core";
import {
  UsersSchema,
  UserSchema,
  type User,
  type UserRole,
} from "../types/auth";

const CreateUserRequestSchema = z.object({
  email: z.string().email(),
  display_name: z.string().min(1),
  password: z.string().min(1),
  role: z.custom<UserRole>(),
  must_change_password: z.boolean().default(true),
  school_id: z.number().int().nullable().optional(),
});
export type CreateUserRequest = z.infer<typeof CreateUserRequestSchema>;

const UpdateUserRequestSchema = z.object({
  display_name: z.string().min(1).optional(),
  role: z.custom<UserRole>().optional(),
  is_active: z.boolean().optional(),
  school_id: z.number().int().nullable().optional(),
});
export type UpdateUserRequest = z.infer<typeof UpdateUserRequestSchema>;

const AdminResetPasswordRequestSchema = z.object({
  new_password: z.string().min(1),
  must_change_password: z.boolean().default(true),
});
export type AdminResetPasswordRequest = z.infer<
  typeof AdminResetPasswordRequestSchema
>;

export const adminUsersApi = {
  listUsers: async (): Promise<User[]> =>
    fetchApi("/api/auth/users", undefined, UsersSchema),

  createUser: async (payload: CreateUserRequest): Promise<User> => {
    const body = CreateUserRequestSchema.parse(payload);
    return fetchApi("/api/auth/users", {
      method: "POST",
      body: JSON.stringify(body),
    }, UserSchema);
  },

  updateUser: async (userId: string, patch: UpdateUserRequest): Promise<User> => {
    const body = UpdateUserRequestSchema.parse(patch);
    return fetchApi(`/api/auth/users/${encodeURIComponent(userId)}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }, UserSchema);
  },

  resetPassword: async (userId: string, payload: AdminResetPasswordRequest): Promise<void> => {
    const body = AdminResetPasswordRequestSchema.parse(payload);
    await fetchApi(`/api/auth/users/${encodeURIComponent(userId)}/reset-password`, {
      method: "POST",
      body: JSON.stringify(body),
    });
  },

  resetMfa: async (userId: string): Promise<void> => {
    await fetchApi(`/api/auth/users/${encodeURIComponent(userId)}/reset-mfa`, {
      method: "POST",
      body: JSON.stringify({}),
    });
  },
};

