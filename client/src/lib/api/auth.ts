import { API_BASE_URL } from "./core";

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface UserResponse {
  id: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  school_id: string;
}

export interface RegisterData {
  email: string;
  password: string;
  full_name: string;
  role: string;
}

export const authApi = {
  login: async (
    email: string,
    password: string,
  ): Promise<TokenResponse> => {
    const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new Error(data.detail || "Login failed");
    }
    return response.json();
  },

  me: async (token: string): Promise<UserResponse> => {
    const response = await fetch(`${API_BASE_URL}/api/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!response.ok) {
      throw new Error("Failed to fetch user");
    }
    return response.json();
  },

  register: async (data: RegisterData): Promise<UserResponse> => {
    const response = await fetch(`${API_BASE_URL}/api/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || "Registration failed");
    }
    return response.json();
  },
};
