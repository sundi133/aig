import { api } from "@/lib/api";
import { StatusTag } from "@/components/StatusTag";

import { DisableToolButton } from "./actions";

interface Tool {
  tool_id: string;
  display_name: string;
  owner_team: string;
  risk_level: string;
  allowed_actions: string[];
  approval_required_by_default: boolean;
  status: string;
}

export default async function ToolsPage() {
  const tools = await api<Tool[]>("/v1/tools");
  return (
    <>
      <h2>Tools</h2>
      {tools.length === 0 ? (
        <div className="empty">No tools registered yet.</div>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Tool ID</th>
              <th>Display name</th>
              <th>Owner</th>
              <th>Risk</th>
              <th>Actions</th>
              <th>Approval default</th>
              <th>Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {tools.map((t) => (
              <tr key={t.tool_id}>
                <td className="mono">{t.tool_id}</td>
                <td>{t.display_name}</td>
                <td>{t.owner_team}</td>
                <td>{t.risk_level}</td>
                <td className="mono">{(t.allowed_actions || []).join(", ") || "*"}</td>
                <td>{t.approval_required_by_default ? "yes" : "no"}</td>
                <td>
                  <StatusTag value={t.status} />
                </td>
                <td>{t.status === "active" && <DisableToolButton toolId={t.tool_id} />}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </>
  );
}
