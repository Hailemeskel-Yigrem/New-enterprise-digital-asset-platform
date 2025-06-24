import { clearTokens, getAccessToken, getRefreshToken, setTokens } from "@/lib/auth/store";
import type { ApiError, TokenResponse } from "@/lib/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export class ApiClientError extends Error {
  constructor(
    message: string,
    public status: number,
    public body?: ApiError,
  ) {
    super(message);
    this.name = "ApiClientError";
  }
}

async function refreshAccessToken(): Promise<string | null> {
  const refresh = getRefreshToken();
  if (!refresh) return null;

  const res = await fetch(`${API_URL}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refresh }),
  });

  if (!res.ok) {
    clearTokens();
    return null;
  }

  const data: TokenResponse = await res.json();
  setTokens(data.access_token, data.refresh_token);
  return data.access_token;
}

export interface RequestOptions extends Omit<RequestInit, "body"> {
  body?: unknown;
  auth?: boolean;
}

export async function apiClient<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const { body, auth = true, headers: customHeaders, ...rest } = options;

  const headers: Record<string, string> = {
    ...(customHeaders as Record<string, string>),
  };

  if (body !== undefined && !(body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  if (auth) {
    const token = getAccessToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;
  }

  let res = await fetch(`${API_URL}${path}`, {
    ...rest,
    headers,
    body:
      body instanceof FormData
        ? body
        : body !== undefined
          ? JSON.stringify(body)
          : undefined,
  });

  if (res.status === 401 && auth) {
    const newToken = await refreshAccessToken();
    if (newToken) {
      headers["Authorization"] = `Bearer ${newToken}`;
      res = await fetch(`${API_URL}${path}`, {
        ...rest,
        headers,
        body:
          body instanceof FormData
            ? body
            : body !== undefined
              ? JSON.stringify(body)
              : undefined,
      });
    }
  }

  if (!res.ok) {
    let errorBody: ApiError | undefined;
    try {
      errorBody = await res.json();
    } catch {
      /* empty */
    }
    const message =
      typeof errorBody?.detail === "string"
        ? errorBody.detail
        : `Request failed (${res.status})`;
    throw new ApiClientError(message, res.status, errorBody);
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}
