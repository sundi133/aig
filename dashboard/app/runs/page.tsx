import { api } from "@/lib/api";
import { StatusTag } from "@/components/StatusTag";

interface AgentRun {
  agent_run_id: string;
  agent_id: string;
  tenant_id: string;
  delegated_user_id: string | null;
  purpose: string;
  allowed_tools: string[];
  status: string;
  created_at: string;
  expires_at: string;
}

export default async function RunsPage({ searchParams }: { searchParams: { agent_id?: string; tenant_id?: string } }) {
  const runs = await api<AgentRun[]>("/v1/agent-runs", {
    query: { agent_id: searchParams.agent_id, tenant_id: searchParams.tenant_id, limit: 200 },
  });

  return (
    <>
      <h2>Agent runs</h2>
      <form className="filters" method="get">
        <input name="agent_id" placeholder="agent_id" defaultValue={searchParams.agent_id || ""} />
        <input name="tenant_id" placeholder="tenant_id" defaultValue={searchParams.tenant_id || ""} />
        <button type="submit">Filter</button>
      </form>
      {runs.length === 0 ? (
        <div className="empty">No agent runs yet.</div>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Run ID</th>
              <th>Agent</th>
              <th>Tenant</th>
              <th>Delegated user</th>
              <th>Purpose</th>
              <th>Allowed tools</th>
              <th>Status</th>
              <th>Expires</th>
            </tr>
          </thead>
          <tbody>
            {runs.map((r) => (
              <tr key={r.agent_run_id}>
                <td className="mono">{r.agent_run_id}</td>
                <td className="mono">{r.agent_id}</td>
                <td className="mono">{r.tenant_id}</td>
                <td className="mono">{r.delegated_user_id || ""}</td>
                <td>{r.purpose}</td>
                <td className="mono">{(r.allowed_tools || []).join(", ")}</td>
                <td>
                  <StatusTag value={r.status} />
                </td>
                <td className="mono">{new Date(r.expires_at).toISOString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </>
  );
}
