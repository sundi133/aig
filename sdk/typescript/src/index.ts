// Agentic AI Identity Gateway -- TypeScript SDK.

export interface RunToken {
  agent_run_id: string;
  access_token: string;
  expires_in: number;
  issued_at: number; // seconds since epoch (client clock)
}

export interface AuthorizeResult {
  decision: "allow" | "deny" | "require_approval";
  reason: string;
  reason_code: string;
  decision_id: string;
  approval_id?: string | null;
  correlation_id?: string | null;
}

export class AIGError extends Error {
  status?: number;
  body?: unknown;
  constructor(message: string, opts: { status?: number; body?: unknown } = {}) {
    super(message);
    this.name = "AIGError";
    this.status = opts.status;
    this.body = opts.body;
  }
}

export interface AIGClientOptions {
  baseUrl: string;
  adminToken?: string;
  fetchImpl?: typeof fetch;
}

interface CreateRunInput {
  agent_id: string;
  tenant_id: string;
  purpose: string;
  delegated_user_id?: string;
  requested_tools?: string[];
  ttl_seconds?: number;
  scopes?: string[];
}

interface AuthorizeInput {
  tool_id: string;
  action: string;
  resource?: string;
  risk_level?: "low" | "medium" | "high" | "critical";
  correlation_id?: string;
}

export class AIGClient {
  private baseUrl: string;
  private adminToken?: string;
  private fetchImpl: typeof fetch;
  private runToken: RunToken | null = null;

  constructor(opts: AIGClientOptions) {
    this.baseUrl = opts.baseUrl.replace(/\/$/, "");
    this.adminToken = opts.adminToken;
    this.fetchImpl = opts.fetchImpl ?? fetch;
  }

  get currentRun(): RunToken | null {
    return this.runToken;
  }

  isRunExpired(leewaySeconds = 5): boolean {
    if (!this.runToken) return true;
    const now = Date.now() / 1000;
    return now + leewaySeconds >= this.runToken.issued_at + this.runToken.expires_in;
  }

  private async request<T>(method: string, path: string, body?: unknown): Promise<T> {
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (this.adminToken) headers["Authorization"] = `Bearer ${this.adminToken}`;

    const resp = await this.fetchImpl(`${this.baseUrl}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    if (!resp.ok) {
      let parsed: unknown;
      try {
        parsed = await resp.json();
      } catch {
        parsed = await resp.text();
      }
      throw new AIGError(`AIG ${method} ${path} failed: ${resp.status}`, {
        status: resp.status,
        body: parsed,
      });
    }
    if (resp.status === 204) return undefined as unknown as T;
    return (await resp.json()) as T;
  }

  async registerAgent(input: Record<string, unknown>): Promise<Record<string, unknown>> {
    return this.request("POST", "/v1/agents", input);
  }

  async registerTool(input: Record<string, unknown>): Promise<Record<string, unknown>> {
    return this.request("POST", "/v1/tools", input);
  }

  async startRun(input: CreateRunInput): Promise<RunToken> {
    const issued_at = Date.now() / 1000;
    const resp = await this.request<{
      agent_run_id: string;
      access_token: string;
      expires_in: number;
    }>("POST", "/v1/agent-runs", {
      ttl_seconds: 900,
      ...input,
    });
    this.runToken = { ...resp, issued_at };
    return this.runToken;
  }

  async authorize(input: AuthorizeInput): Promise<AuthorizeResult> {
    if (!this.runToken) {
      throw new AIGError("No active run -- call startRun() first");
    }
    if (this.isRunExpired()) {
      throw new AIGError("Run token expired -- start a new run");
    }
    return this.request<AuthorizeResult>("POST", "/v1/authorize", {
      access_token: this.runToken.access_token,
      ...input,
    });
  }

  async searchAuditEvents(filters: Record<string, string | number> = {}): Promise<unknown[]> {
    const q = new URLSearchParams(filters as Record<string, string>).toString();
    return this.request("GET", `/v1/audit-events${q ? `?${q}` : ""}`);
  }

  async listApprovals(filters: Record<string, string | number> = {}): Promise<unknown[]> {
    const q = new URLSearchParams(filters as Record<string, string>).toString();
    return this.request("GET", `/v1/approvals${q ? `?${q}` : ""}`);
  }

  async resolveApproval(
    approvalId: string,
    body: { decision: "approved" | "rejected"; resolver_id: string; note?: string },
  ): Promise<unknown> {
    return this.request("POST", `/v1/approvals/${approvalId}/resolve`, body);
  }
}
