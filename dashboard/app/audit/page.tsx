import { api } from "@/lib/api";
import { StatusTag } from "@/components/StatusTag";

interface AuditEvent {
  event_id: string;
  timestamp: string;
  event_type: string;
  tenant_id: string | null;
  agent_id: string | null;
  agent_run_id: string | null;
  delegated_user_id: string | null;
  tool_id: string | null;
  action: string | null;
  resource: string | null;
  decision: string | null;
  reason_code: string | null;
  actor_id: string | null;
  correlation_id: string | null;
}

export default async function AuditPage({ searchParams }: { searchParams: Record<string, string | undefined> }) {
  const events = await api<AuditEvent[]>("/v1/audit-events", {
    query: { ...searchParams, limit: 200 },
  });

  return (
    <>
      <h2>Audit log</h2>
      <form className="filters" method="get">
        <input name="agent_id" placeholder="agent_id" defaultValue={searchParams.agent_id || ""} />
        <input name="agent_run_id" placeholder="agent_run_id" defaultValue={searchParams.agent_run_id || ""} />
        <input name="tenant_id" placeholder="tenant_id" defaultValue={searchParams.tenant_id || ""} />
        <input name="tool_id" placeholder="tool_id" defaultValue={searchParams.tool_id || ""} />
        <input name="action" placeholder="action" defaultValue={searchParams.action || ""} />
        <input name="decision" placeholder="decision" defaultValue={searchParams.decision || ""} />
        <input name="event_type" placeholder="event_type" defaultValue={searchParams.event_type || ""} />
        <input name="correlation_id" placeholder="correlation_id" defaultValue={searchParams.correlation_id || ""} />
        <button type="submit">Search</button>
      </form>

      {events.length === 0 ? (
        <div className="empty">No matching events.</div>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>Event type</th>
              <th>Agent / Run</th>
              <th>Tenant / User</th>
              <th>Tool : Action</th>
              <th>Resource</th>
              <th>Decision</th>
              <th>Reason</th>
              <th>Correlation</th>
            </tr>
          </thead>
          <tbody>
            {events.map((e) => (
              <tr key={e.event_id}>
                <td className="mono">{new Date(e.timestamp).toISOString()}</td>
                <td className="mono">{e.event_type}</td>
                <td className="mono">
                  {e.agent_id || ""}
                  {e.agent_run_id ? <div className="muted">{e.agent_run_id}</div> : null}
                </td>
                <td className="mono">
                  {e.tenant_id || ""}
                  {e.delegated_user_id ? <div className="muted">{e.delegated_user_id}</div> : null}
                </td>
                <td className="mono">
                  {e.tool_id || ""}
                  {e.action ? `:${e.action}` : ""}
                </td>
                <td className="mono">{e.resource || ""}</td>
                <td>{e.decision ? <StatusTag value={e.decision} /> : ""}</td>
                <td className="mono">{e.reason_code || ""}</td>
                <td className="mono">{e.correlation_id || ""}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </>
  );
}
