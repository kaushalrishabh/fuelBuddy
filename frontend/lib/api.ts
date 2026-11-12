const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const CSRF_HEADER = "X-FuelBuddy-Client";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

/** FastAPI's `detail` is a string for a raised HTTPException, but an array
 * of {msg, loc, ...} objects for a Pydantic request-validation (422) error. */
function extractErrorMessage(detail: unknown, fallback: string): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => (item && typeof item === "object" && "msg" in item ? String(item.msg) : null))
      .filter((msg): msg is string => Boolean(msg));
    if (messages.length > 0) return messages.join("; ");
  }
  return fallback;
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const isFormData = init.body instanceof FormData;

  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    credentials: "include",
    headers: {
      [CSRF_HEADER]: "web",
      ...(init.body && !isFormData ? { "Content-Type": "application/json" } : {}),
      ...init.headers,
    },
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new ApiError(response.status, extractErrorMessage(body?.detail, response.statusText));
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, {
      method: "POST",
      body: body !== undefined ? JSON.stringify(body) : undefined,
    }),
  patch: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "PATCH", body: JSON.stringify(body) }),
  postForm: <T>(path: string, form: FormData) => request<T>(path, { method: "POST", body: form }),
};

export function downloadUrl(path: string): string {
  return `${API_URL}${path}`;
}
