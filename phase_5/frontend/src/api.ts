import { getAuth } from "firebase/auth";

const BASE_URL = (import.meta.env.VITE_API_URL || "http://localhost:8080").replace(/\/+$/, "") + "/api/v1";

export interface APIResponse<T> {
  success: boolean;
  data?: T;
  error?: {
    code: string;
    message: string;
  };
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers || {});
  headers.set("Content-Type", "application/json");

  // Fetch token from Firebase Auth if user logged in and auth is initialized
  try {
    const auth = getAuth();
    if (auth && auth.currentUser) {
      const token = await auth.currentUser.getIdToken();
      if (token) {
        headers.set("Authorization", `Bearer ${token}`);
      }
    }
  } catch (err) {
    console.debug("Firebase Auth not initialized or bypassed in single-user mode:", err);
  }

  const response = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers,
  });

  if (response.status === 204) {
    return { success: true } as unknown as T;
  }

  let body: APIResponse<any>;
  try {
    body = await response.json();
  } catch (err) {
    throw new Error(`Invalid JSON response: ${response.statusText}`);
  }

  if (!body.success) {
    throw new Error(body.error?.message || "An unknown server error occurred");
  }

  return body.data as T;
}

export const api = {
  get: <T>(path: string) => request<T>(path, { method: "GET" }),
  post: <T>(path: string, data: any) => request<T>(path, { method: "POST", body: JSON.stringify(data) }),
  put: <T>(path: string, data: any) => request<T>(path, { method: "PUT", body: JSON.stringify(data) }),
  patch: <T>(path: string, data: any) => request<T>(path, { method: "PATCH", body: JSON.stringify(data) }),
  delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),
  
  // Stream PDF directly
  getResumePDFURL: (jobId: string): string => {
    return `${BASE_URL}/jobs/${jobId}/resume`;
  }
};
