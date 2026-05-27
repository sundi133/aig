"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

export function DisableAgentButton({ agentId }: { agentId: string }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  return (
    <button
      className="danger"
      disabled={busy}
      onClick={async () => {
        if (!confirm(`Disable agent ${agentId}?`)) return;
        setBusy(true);
        try {
          const resp = await fetch(`/api/agents/${encodeURIComponent(agentId)}/disable`, { method: "POST" });
          if (!resp.ok) alert(`Failed: ${await resp.text()}`);
          router.refresh();
        } finally {
          setBusy(false);
        }
      }}
    >
      Disable
    </button>
  );
}
