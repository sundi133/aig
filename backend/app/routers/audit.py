from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..auth import require_admin
from ..db import get_db
from ..models import AuditEvent
from ..schemas import AuditEventRead

router = APIRouter(prefix="/v1/audit-events", tags=["audit"])


@router.get("", response_model=List[AuditEventRead])
def search_audit_events(
    db: Session = Depends(get_db),
    actor: str = Depends(require_admin),
    agent_id: Optional[str] = Query(default=None),
    agent_run_id: Optional[str] = Query(default=None),
    tenant_id: Optional[str] = Query(default=None),
    delegated_user_id: Optional[str] = Query(default=None),
    tool_id: Optional[str] = Query(default=None),
    action: Optional[str] = Query(default=None),
    decision: Optional[str] = Query(default=None),
    event_type: Optional[str] = Query(default=None),
    correlation_id: Optional[str] = Query(default=None),
    since: Optional[datetime] = Query(default=None),
    until: Optional[datetime] = Query(default=None),
    limit: int = Query(default=100, le=1000),
) -> List[AuditEventRead]:
    q = db.query(AuditEvent)
    if agent_id:
        q = q.filter(AuditEvent.agent_id == agent_id)
    if agent_run_id:
        q = q.filter(AuditEvent.agent_run_id == agent_run_id)
    if tenant_id:
        q = q.filter(AuditEvent.tenant_id == tenant_id)
    if delegated_user_id:
        q = q.filter(AuditEvent.delegated_user_id == delegated_user_id)
    if tool_id:
        q = q.filter(AuditEvent.tool_id == tool_id)
    if action:
        q = q.filter(AuditEvent.action == action)
    if decision:
        q = q.filter(AuditEvent.decision == decision)
    if event_type:
        q = q.filter(AuditEvent.event_type == event_type)
    if correlation_id:
        q = q.filter(AuditEvent.correlation_id == correlation_id)
    if since:
        q = q.filter(AuditEvent.timestamp >= since)
    if until:
        q = q.filter(AuditEvent.timestamp <= until)
    rows = q.order_by(AuditEvent.timestamp.desc()).limit(limit).all()
    return [AuditEventRead.from_model(r) for r in rows]
