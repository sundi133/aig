import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from .. import audit
from ..auth import require_admin
from ..db import get_db
from ..models import Approval
from ..schemas import ApprovalCreate, ApprovalRead, ApprovalResolve

router = APIRouter(prefix="/v1/approvals", tags=["approvals"])


@router.post("", response_model=ApprovalRead, status_code=status.HTTP_201_CREATED)
def create_approval(
    body: ApprovalCreate,
    db: Session = Depends(get_db),
    actor: str = Depends(require_admin),
) -> ApprovalRead:
    approval = Approval(
        approval_id=f"app_{uuid.uuid4().hex[:24]}",
        agent_id=body.agent_id,
        agent_run_id=body.agent_run_id,
        tenant_id=body.tenant_id,
        delegated_user_id=body.delegated_user_id,
        tool_id=body.tool_id,
        action=body.action,
        resource=body.resource,
        reason=body.reason,
        status="pending",
    )
    db.add(approval)
    audit.write_event(
        db,
        event_type="approval.requested",
        tenant_id=body.tenant_id,
        agent_id=body.agent_id,
        agent_run_id=body.agent_run_id,
        delegated_user_id=body.delegated_user_id,
        actor_id=actor,
        tool_id=body.tool_id,
        action=body.action,
        resource=body.resource,
        metadata={"approval_id": approval.approval_id},
    )
    db.commit()
    db.refresh(approval)
    return ApprovalRead.model_validate(approval)


@router.get("", response_model=List[ApprovalRead])
def list_approvals(
    db: Session = Depends(get_db),
    actor: str = Depends(require_admin),
    status_filter: Optional[str] = Query(default=None, alias="status"),
    tenant_id: Optional[str] = Query(default=None),
    limit: int = Query(default=100, le=500),
) -> List[ApprovalRead]:
    q = db.query(Approval)
    if status_filter:
        q = q.filter(Approval.status == status_filter)
    if tenant_id:
        q = q.filter(Approval.tenant_id == tenant_id)
    rows = q.order_by(Approval.created_at.desc()).limit(limit).all()
    return [ApprovalRead.model_validate(r) for r in rows]


@router.get("/{approval_id}", response_model=ApprovalRead)
def get_approval(
    approval_id: str,
    db: Session = Depends(get_db),
    actor: str = Depends(require_admin),
) -> ApprovalRead:
    approval = db.get(Approval, approval_id)
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    return ApprovalRead.model_validate(approval)


@router.post("/{approval_id}/resolve", response_model=ApprovalRead)
def resolve_approval(
    approval_id: str,
    body: ApprovalResolve,
    db: Session = Depends(get_db),
    actor: str = Depends(require_admin),
) -> ApprovalRead:
    approval = db.get(Approval, approval_id)
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    if approval.status != "pending":
        raise HTTPException(status_code=409, detail=f"Approval already {approval.status}")
    approval.status = body.decision
    approval.resolver_id = body.resolver_id
    approval.resolution_note = body.note
    approval.resolved_at = datetime.now(timezone.utc)

    audit.write_event(
        db,
        event_type="approval.resolved",
        tenant_id=approval.tenant_id,
        agent_id=approval.agent_id,
        agent_run_id=approval.agent_run_id,
        delegated_user_id=approval.delegated_user_id,
        actor_id=actor,
        tool_id=approval.tool_id,
        action=approval.action,
        resource=approval.resource,
        decision=approval.status,
        metadata={"approval_id": approval.approval_id, "resolver_id": body.resolver_id},
    )
    db.commit()
    db.refresh(approval)
    return ApprovalRead.model_validate(approval)
