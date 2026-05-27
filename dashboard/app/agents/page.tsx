import { api } from "@/lib/api";
import { StatusTag } from "@/components/StatusTag";

import { DisableAgentButton } from "./actions";

interface Agent {
  agent_id: string;
  display_name: string;
  owner_team: string;
  environment: string;
  status: string;
  allowed_tools: string[];
  default_scopes: string[];
  created_at: string;
}

export default async function AgentsPage() {
  const agents = await api<Agent[]>("/v1/agents");
  return (
    <>
      <h2>Agents</h2>
      {agents.length === 0 ? (
        <div className="empty">
          No agents registered yet. Use <code className="mono">POST /v1/agents</code> or the Python SDK to register one.
        </div>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Agent ID</th>
              <th>Display name</th>
              <th>Owner</th>
              <th>Env</th>
              <th>Status</th>
              <th>Allowed tools</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {agents.map((a) => (
              <tr key={a.agent_id}>
                <td className="mono">{a.agent_id}</td>
                <td>{a.display_name}</td>
                <td>{a.owner_team}</td>
                <td>{a.environment}</td>
                <td>
                  <StatusTag value={a.status} />
                </td>
                <td className="mono">{(a.allowed_tools || []).join(", ") || "*"}</td>
                <td>{a.status === "active" && <DisableAgentButton agentId={a.agent_id} />}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </>
  );
}
