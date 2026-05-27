"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

export function DisableToolButton({ toolId }: { toolId: string }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  return (
    <button
      className="danger"
      disabled={busy}
      onClick={async () => {
        if (!confirm(`Disable tool ${toolId}?`)) return;
        setBusy(true);
        try {
          const resp = await fetch(`/api/tools/${encodeURIComponent(toolId)}/disable`, { method: "POST" });
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
