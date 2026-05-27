"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

export function ResolveApprovalButtons({ approvalId }: { approvalId: string }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);

  async function resolve(decision: "approved" | "rejected") {
    const resolver = prompt("Your operator ID (e.g. user:jane@example.com):");
    if (!resolver) return;
    setBusy(true);
    try {
      const resp = await fetch(`/api/approvals/${encodeURIComponent(approvalId)}/resolve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ decision, resolver_id: resolver }),
      });
      if (!resp.ok) alert(`Failed: ${await resp.text()}`);
      router.refresh();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div style={{ display: "flex", gap: 6 }}>
      <button disabled={busy} onClick={() => resolve("approved")}>
        Approve
      </button>
      <button className="danger" disabled={busy} onClick={() => resolve("rejected")}>
        Reject
      </button>
    </div>
  );
}
