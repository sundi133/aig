import { api } from "@/lib/api";
import { StatusTag } from "@/components/StatusTag";

import { ResolveApprovalButtons } from "./actions";

interface Approval {
  approval_id: string;
  agent_id: string;
  agent_run_id: string;
  tenant_id: string;
  delegated_user_id: string | null;
  tool_id: string;
  action: string;
  resource: string | null;
  reason: string | null;
  status: string;
  created_at: string;
  resolved_at: string | null;
  resolver_id: string | null;
}

export default async function ApprovalsPage({ searchParams }: { searchParams: { status?: string } }) {
  const status = searchParams.status || "pending";
  const approvals = await api<Approval[]>("/v1/approvals", {
    query: { status, limit: 200 },
  });

  return (
    <>
      <h2>Approvals</h2>
      <form className="filters" method="get">
        <select name="status" defaultValue={status}>
          <option value="pending">Pending</option>
          <option value="approved">Approved</option>
          <option value="rejected">Rejected</option>
        </select>
        <button type="submit">Filter</button>
      </form>

      {approvals.length === 0 ? (
        <div className="empty">No {status} approvals.</div>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Approval ID</th>
              <th>Agent / Run</th>
              <th>Tenant / User</th>
              <th>Tool : Action</th>
              <th>Resource</th>
              <th>Reason</th>
              <th>Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {approvals.map((a) => (
              <tr key={a.approval_id}>
                <td className="mono">{a.approval_id}</td>
                <td className="mono">
                  {a.agent_id}
                  <div className="muted">{a.agent_run_id}</div>
                </td>
                <td className="mono">
                  {a.tenant_id}
                  {a.delegated_user_id ? <div className="muted">{a.delegated_user_id}</div> : null}
                </td>
                <td className="mono">
                  {a.tool_id}:{a.action}
                </td>
                <td className="mono">{a.resource || ""}</td>
                <td>{a.reason}</td>
                <td>
                  <StatusTag value={a.status} />
                </td>
                <td>
                  {a.status === "pending" && <ResolveApprovalButtons approvalId={a.approval_id} />}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </>
  );
}
