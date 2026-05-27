// Server-side helpers that talk to the backend. The admin token never leaves
// the server -- the UI talks to Next.js route handlers, not directly to the
// backend.

const BACKEND_URL = process.env.AIG_BACKEND_URL || "http://localhost:8080";
const ADMIN_TOKEN = process.env.AIG_ADMIN_TOKEN || "admin-dev-token";

export type FetchOptions = {
  method?: string;
  body?: unknown;
  query?: Record<string, string | number | undefined>;
  cache?: RequestCache;
};

export async function api<T = unknown>(path: string, opts: FetchOptions = {}): Promise<T> {
  const qs = opts.query
    ? "?" +
      new URLSearchParams(
        Object.entries(opts.query)
          .filter(([, v]) => v !== undefined && v !== "")
          .map(([k, v]) => [k, String(v)]),
      ).toString()
    : "";

  const resp = await fetch(`${BACKEND_URL}${path}${qs}`, {
    method: opts.method || "GET",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${ADMIN_TOKEN}`,
    },
    body: opts.body ? JSON.stringify(opts.body) : undefined,
    cache: opts.cache ?? "no-store",
  });

  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`Backend ${opts.method || "GET"} ${path} ${resp.status}: ${text}`);
  }
  if (resp.status === 204) return undefined as unknown as T;
  return (await resp.json()) as T;
}

export const backendUrl = BACKEND_URL;
