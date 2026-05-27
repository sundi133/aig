# @aig/sdk (TypeScript)

TypeScript SDK for the Agentic AI Identity Gateway.

```ts
import { AIGClient } from "@aig/sdk";

const aig = new AIGClient({
  baseUrl: "http://localhost:8080",
  adminToken: process.env.AIG_TOKEN,
});

await aig.startRun({
  agent_id: "research-agent",
  tenant_id: "tenant_123",
  delegated_user_id: "user_456",
  purpose: "summarize_contract",
  requested_tools: ["document_search"],
});

const result = await aig.authorize({ tool_id: "document_search", action: "read", resource: "doc_789" });
if (result.decision === "allow") {
  // call the tool
}
```
