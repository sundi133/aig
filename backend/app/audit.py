"""Audit log helpers."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from .models import AuditEvent


def write_event(
    db: Session,
    *,
    event_type: str,
    tenant_id: Optional[str] = None,
    agent_id: Optional[str] = None,
    agent_run_id: Optional[str] = None,
    delegated_user_id: Optional[str] = None,
    actor_id: Optional[str] = None,
    tool_id: Optional[str] = None,
    action: Optional[str] = None,
    resource: Optional[str] = None,
    decision: Optional[str] = None,
    reason_code: Optional[str] = None,
    correlation_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> AuditEvent:
    event = AuditEvent(
        event_id=f"evt_{uuid.uuid4().hex[:24]}",
        timestamp=datetime.now(timezone.utc),
        event_type=event_type,
        tenant_id=tenant_id,
        agent_id=agent_id,
        agent_run_id=agent_run_id,
        delegated_user_id=delegated_user_id,
        actor_id=actor_id,
        tool_id=tool_id,
        action=action,
        resource=resource,
        decision=decision,
        reason_code=reason_code,
        correlation_id=correlation_id,
        event_metadata=metadata or {},
    )
    db.add(event)
    db.flush()
    return event
