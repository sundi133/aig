# aig-sdk (Python)

Python SDK for the Agentic AI Identity Gateway.

```python
from aig_sdk import AIGAgentClient

with AIGAgentClient("http://localhost:8080", admin_token="admin-dev-token") as aig:
    aig.start_run(
        agent_id="research-agent",
        tenant_id="tenant_123",
        delegated_user_id="user_456",
        purpose="summarize_contract",
        requested_tools=["document_search"],
    )

    decision = aig.authorize(
        tool_id="document_search",
        action="read",
        resource="doc_789",
    )

    if decision.allowed:
        ...  # safe to call the tool
    elif decision.decision == "require_approval":
        ...  # wait for approval
    else:
        ...  # tool call is denied
```
