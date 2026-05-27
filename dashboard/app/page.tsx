import Link from "next/link";

import { api } from "@/lib/api";

interface Agent {
  agent_id: string;
  status: string;
}
interface Tool {
  tool_id: string;
  status: string;
}
interface Run {
  agent_run_id: string;
}
interface Approval {
  approval_id: string;
  status: string;
}

export default async function OverviewPage() {
  let agents: Agent[] = [];
  let tools: Tool[] = [];
  let runs: Run[] = [];
  let approvals: Approval[] = [];
  let err: string | null = null;

  try {
    [agents, tools, runs, approvals] = await Promise.all([
      api<Agent[]>("/v1/agents"),
      api<Tool[]>("/v1/tools"),
      api<Run[]>("/v1/agent-runs", { query: { limit: 500 } }),
      api<Approval[]>("/v1/approvals", { query: { status: "pending", limit: 500 } }),
    ]);
  } catch (e) {
    err = (e as Error).message;
  }

  return (
    <>
      <h2>Overview</h2>
      {err && (
        <div className="empty" style={{ borderColor: "var(--red)", color: "var(--red)" }}>
          Could not reach backend: {err}
        </div>
      )}
      <div className="kpi-row">
        <div className="kpi">
          <div className="label">Active agents</div>
          <div className="value">{agents.filter((a) => a.status === "active").length}</div>
          <div className="muted" style={{ marginTop: 6 }}>
            {agents.length} total
          </div>
        </div>
        <div className="kpi">
          <div className="label">Active tools</div>
          <div className="value">{tools.filter((t) => t.status === "active").length}</div>
          <div className="muted" style={{ marginTop: 6 }}>
            {tools.length} total
          </div>
        </div>
        <div className="kpi">
          <div className="label">Agent runs</div>
          <div className="value">{runs.length}</div>
        </div>
        <div className="kpi">
          <div className="label">Pending approvals</div>
          <div className="value">{approvals.length}</div>
        </div>
      </div>

      <p className="muted">
        Start at <Link href="/agents">Agents</Link> to register an agent, then{" "}
        <Link href="/tools">Tools</Link> to register tools it may call. View{" "}
        <Link href="/runs">Agent runs</Link> for active sessions and the{" "}
        <Link href="/audit">Audit log</Link> for a complete record of every
        token issuance and authorization decision.
      </p>
    </>
  );
}
