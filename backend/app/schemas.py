from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator


# ---------- Agents ----------

class AgentCreate(BaseModel):
    agent_id: str = Field(min_length=1, max_length=128)
    display_name: str
    owner_team: str
    environment: str = "dev"
    keycloak_client_id: str = ""
    default_scopes: List[str] = Field(default_factory=list)
    allowed_tools: List[str] = Field(default_factory=list)
    status: Literal["active", "disabled"] = "active"


class AgentUpdate(BaseModel):
    display_name: Optional[str] = None
    owner_team: Optional[str] = None
    environment: Optional[str] = None
    keycloak_client_id: Optional[str] = None
    default_scopes: Optional[List[str]] = None
    allowed_tools: Optional[List[str]] = None
    status: Optional[Literal["active", "disabled"]] = None


class AgentRead(BaseModel):
    agent_id: str
    display_name: str
    owner_team: str
    environment: str
    keycloak_client_id: str
    status: str
    default_scopes: List[str] = Field(default_factory=list)
    allowed_tools: List[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ---------- Tools ----------

class ToolCreate(BaseModel):
    tool_id: str
    display_name: str
    owner_team: str
    risk_level: Literal["low", "medium", "high", "critical"] = "low"
    allowed_actions: List[str] = Field(default_factory=list)
    approval_required_by_default: bool = False
    status: Literal["active", "disabled", "deprecated"] = "active"


class ToolUpdate(BaseModel):
    display_name: Optional[str] = None
    owner_team: Optional[str] = None
    risk_level: Optional[Literal["low", "medium", "high", "critical"]] = None
    allowed_actions: Optional[List[str]] = None
    approval_required_by_default: Optional[bool] = None
    status: Optional[Literal["active", "disabled", "deprecated"]] = None


class ToolRead(BaseModel):
    tool_id: str
    display_name: str
    owner_team: str
    risk_level: str
    allowed_actions: List[str] = Field(default_factory=list)
    approval_required_by_default: bool
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ---------- Agent runs ----------

class AgentRunCreate(BaseModel):
    agent_id: str
    tenant_id: str
    delegated_user_id: Optional[str] = None
    purpose: str
    requested_tools: List[str] = Field(default_factory=list)
    ttl_seconds: int = 900
    scopes: List[str] = Field(default_factory=list)

    @field_validator("ttl_seconds")
    @classmethod
    def _ttl_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("ttl_seconds must be positive")
        return v


class AgentRunCreateResponse(BaseModel):
    agent_run_id: str
    access_token: str
    expires_in: int
    token_type: str = "Bearer"


class AgentRunRead(BaseModel):
    agent_run_id: str
    agent_id: str
    tenant_id: str
    delegated_user_id: Optional[str]
    purpose: str
    requested_tools: List[str] = Field(default_factory=list)
    allowed_tools: List[str] = Field(default_factory=list)
    scopes: List[str] = Field(default_factory=list)
    status: str
    created_at: datetime
    expires_at: datetime

    class Config:
        from_attributes = True


# ---------- Authorization ----------

class AuthorizeRequest(BaseModel):
    agent_id: Optional[str] = None
    agent_run_id: Optional[str] = None
    tenant_id: Optional[str] = None
    delegated_user_id: Optional[str] = None
    tool_id: str
    action: str
    resource: Optional[str] = None
    risk_level: Optional[Literal["low", "medium", "high", "critical"]] = None
    correlation_id: Optional[str] = None
    # If supplied, the gateway will decode and trust the run token's claims as
    # the basis for the decision (preferred path -- token claims are signed).
    access_token: Optional[str] = None


class AuthorizeResponse(BaseModel):
    decision: Literal["allow", "deny", "require_approval"]
    reason: str
    reason_code: str
    decision_id: str
    approval_id: Optional[str] = None
    correlation_id: Optional[str] = None


# ---------- Approvals ----------

class ApprovalCreate(BaseModel):
    agent_id: str
    agent_run_id: str
    tenant_id: str
    delegated_user_id: Optional[str] = None
    tool_id: str
    action: str
    resource: Optional[str] = None
    reason: Optional[str] = None


class ApprovalResolve(BaseModel):
    decision: Literal["approved", "rejected"]
    resolver_id: str
    note: Optional[str] = None


class ApprovalRead(BaseModel):
    approval_id: str
    agent_id: str
    agent_run_id: str
    tenant_id: str
    delegated_user_id: Optional[str]
    tool_id: str
    action: str
    resource: Optional[str]
    reason: Optional[str]
    status: str
    resolver_id: Optional[str]
    resolution_note: Optional[str]
    created_at: datetime
    resolved_at: Optional[datetime]

    class Config:
        from_attributes = True


# ---------- Audit ----------

class AuditEventRead(BaseModel):
    event_id: str
    timestamp: datetime
    event_type: str
    tenant_id: Optional[str] = None
    agent_id: Optional[str] = None
    agent_run_id: Optional[str] = None
    delegated_user_id: Optional[str] = None
    actor_id: Optional[str] = None
    tool_id: Optional[str] = None
    action: Optional[str] = None
    resource: Optional[str] = None
    decision: Optional[str] = None
    reason_code: Optional[str] = None
    correlation_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        from_attributes = True

    @classmethod
    def from_model(cls, row: Any) -> "AuditEventRead":
        # SQLAlchemy attr is ``event_metadata`` (because ``metadata`` is reserved
        # on the declarative base) -- normalize to the public ``metadata`` key.
        return cls(
            event_id=row.event_id,
            timestamp=row.timestamp,
            event_type=row.event_type,
            tenant_id=row.tenant_id,
            agent_id=row.agent_id,
            agent_run_id=row.agent_run_id,
            delegated_user_id=row.delegated_user_id,
            actor_id=row.actor_id,
            tool_id=row.tool_id,
            action=row.action,
            resource=row.resource,
            decision=row.decision,
            reason_code=row.reason_code,
            correlation_id=row.correlation_id,
            metadata=row.event_metadata or {},
        )
