const API_PREFIX = "/api/v1";

export class ApiError extends Error {
  status: number;
  body: unknown;

  constructor(status: number, body: unknown) {
    let detail = "Erro na requisicao";
    if (typeof body === "object" && body !== null && "detail" in body) {
      detail = String(body.detail);
    }
    super(detail);
    this.status = status;
    this.body = body;
  }
}

export const GENERIC_LOAD_ERROR_MESSAGE = "Nao foi possivel carregar os dados.";
export const GENERIC_SAVE_ERROR_MESSAGE = "Nao foi possivel salvar.";

/** Extracts a user-facing message from a caught value, falling back for non-API errors. */
export function errorMessage(err: unknown, fallback: string): string {
  return err instanceof ApiError ? err.message : fallback;
}

async function parseBody(response: Response): Promise<unknown> {
  const text = await response.text();
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

async function rawFetch(path: string, init?: RequestInit): Promise<Response> {
  return fetch(`${API_PREFIX}${path}`, {
    ...init,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });
}

export async function apiFetch<T = unknown>(path: string, init?: RequestInit): Promise<T> {
  let response = await rawFetch(path, init);

  if (response.status === 401 && path !== "/auth/refresh" && path !== "/auth/login") {
    const refreshResponse = await rawFetch("/auth/refresh", { method: "POST" });
    if (refreshResponse.ok) {
      response = await rawFetch(path, init);
    } else {
      if (typeof window !== "undefined") {
        const next = encodeURIComponent(window.location.pathname + window.location.search);
        window.location.href = `/login?expired=1&next=${next}`;
      }
      throw new ApiError(401, { detail: "Sessao expirada" });
    }
  }

  const body = await parseBody(response);
  if (!response.ok) {
    throw new ApiError(response.status, body);
  }
  return body as T;
}
