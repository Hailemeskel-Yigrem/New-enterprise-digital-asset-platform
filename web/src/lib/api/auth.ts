import { apiClient } from "@/lib/api/client";
import { clearTokens, setTokens } from "@/lib/auth/store";
import type { TokenResponse, User } from "@/lib/types";
import type { LoginFormValues, RegisterFormValues } from "@/lib/validators/auth";

export async function login(credentials: LoginFormValues): Promise<User> {
  const tokens = await apiClient<TokenResponse>("/auth/login", {
    method: "POST",
    body: credentials,
    auth: false,
  });
  setTokens(tokens.access_token, tokens.refresh_token);
  return getMe();
}

export async function register(data: RegisterFormValues): Promise<User> {
  const { confirm_password: _, ...payload } = data;
  return apiClient<User>("/auth/register", {
    method: "POST",
    body: payload,
    auth: false,
  });
}

export async function getMe(): Promise<User> {
  return apiClient<User>("/auth/me");
}

export function logout(): void {
  clearTokens();
}
