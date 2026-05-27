from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Agent(Base):
    __tablename__ = "agents"

    agent_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(256), nullable=False)
    owner_team: Mapped[str] = mapped_column(String(128), nullable=False)
    environment: Mapped[str] = mapped_column(String(64), nullable=False, default="dev")
    keycloak_client_id: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    default_scopes: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    allowed_tools: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class Tool(Base):
    __tablename__ = "tools"

    tool_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(256), nullable=False)
    owner_team: Mapped[str] = mapped_column(String(128), nullable=False)
    risk_level: Mapped[str] = mapped_column(String(32), nullable=False, default="low")
    allowed_actions: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    approval_required_by_default: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class AgentRun(Base):
    __tablename__ = "agent_runs"

    agent_run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    agent_id: Mapped[str] = mapped_column(String(128), ForeignKey("agents.agent_id"), index=True)
    tenant_id: Mapped[str] = mapped_column(String(128), index=True)
    delegated_user_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    purpose: Mapped[str] = mapped_column(String(256), nullable=False)
    requested_tools: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    allowed_tools: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    scopes: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Approval(Base):
    __tablename__ = "approvals"

    approval_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    agent_id: Mapped[str] = mapped_column(String(128), index=True)
    agent_run_id: Mapped[str] = mapped_column(String(64), index=True)
    tenant_id: Mapped[str] = mapped_column(String(128), index=True)
    delegated_user_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    tool_id: Mapped[str] = mapped_column(String(128))
    action: Mapped[str] = mapped_column(String(128))
    resource: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")  # pending|approved|rejected
    resolver_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    resolution_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    event_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    tenant_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    agent_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    agent_run_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    delegated_user_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    actor_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    tool_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    action: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    resource: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    decision: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, index=True)
    reason_code: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    correlation_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    event_metadata: Mapped[Optional[Any]] = mapped_column("metadata", JSON, nullable=True)


Index("ix_audit_query", AuditEvent.tenant_id, AuditEvent.agent_id, AuditEvent.timestamp)
