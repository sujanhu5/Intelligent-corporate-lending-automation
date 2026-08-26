"""
Rule Engine endpoints.

Admin routes (require admin role):
  POST   /rules                          — create a new banking rule
  PUT    /rules/{rule_id}                — update an existing rule
  DELETE /rules/{rule_id}                — permanently delete a rule
  PATCH  /rules/{rule_id}/toggle         — activate / deactivate a rule

Analyst+ routes:
  GET    /rules                          — list all rules (paginated, filterable)
  GET    /rules/{rule_id}                — retrieve one rule

Evaluation routes (analyst+):
  POST   /rules/evaluate/{application_id} — run the rule engine for an application
  GET    /rules/evaluation/{application_id} — retrieve stored evaluation result
"""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request, Response, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.dependencies import get_client_ip, get_current_user, require_admin, require_analyst
from app.models.rule import RuleCategory
from app.models.user import User
from app.schemas.rule import (
    RuleCreate,
    RuleEngineResponse,
    RuleListResponse,
    RuleResponse,
    RuleUpdate,
)
from app.services.rule_service import RuleService

router = APIRouter()


# ---------------------------------------------------------------------------
# List rules
# ---------------------------------------------------------------------------

@router.get(
    "",
    response_model=RuleListResponse,
    status_code=status.HTTP_200_OK,
    summary="List all banking rules",
    description=(
        "Returns all banking rules with optional filtering by category, "
        "mandatory flag, or active status. Ordered by priority ascending."
    ),
)
def list_rules(
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Results per page"),
    category: Optional[RuleCategory] = Query(
        default=None, description="Filter by rule category"
    ),
    is_mandatory: Optional[bool] = Query(
        default=None, description="Filter mandatory (True) or advisory (False) rules"
    ),
    is_active: Optional[bool] = Query(
        default=None, description="Filter active (True) or inactive (False) rules"
    ),
    current_user: User = Depends(require_analyst),
    db: Session = Depends(get_db),
) -> RuleListResponse:
    return RuleService(db).list_rules(
        page=page,
        page_size=page_size,
        category=category,
        is_mandatory=is_mandatory,
        is_active=is_active,
    )


# ---------------------------------------------------------------------------
# Create rule
# ---------------------------------------------------------------------------

@router.post(
    "",
    response_model=RuleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new banking rule",
    description=(
        "Creates a new evaluation rule. Only administrators can create rules. "
        "Mandatory rules with action 'reject' will cause automatic loan rejection "
        "when triggered. The ML pipeline is bypassed for rejected applications."
    ),
)
def create_rule(
    request: Request,
    payload: RuleCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> RuleResponse:
    return RuleService(db).create_rule(
        payload=payload,
        created_by=current_user,
        ip_address=get_client_ip(request),
        request_id=getattr(request.state, "request_id", "unknown"),
    )


# ---------------------------------------------------------------------------
# Get single rule
# ---------------------------------------------------------------------------

@router.get(
    "/{rule_id}",
    response_model=RuleResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve a single rule by ID",
)
def get_rule(
    rule_id: uuid.UUID,
    current_user: User = Depends(require_analyst),
    db: Session = Depends(get_db),
) -> RuleResponse:
    return RuleService(db).get_rule(rule_id)


# ---------------------------------------------------------------------------
# Update rule
# ---------------------------------------------------------------------------

@router.put(
    "/{rule_id}",
    response_model=RuleResponse,
    status_code=status.HTTP_200_OK,
    summary="Update an existing rule",
    description=(
        "Updates rule fields. Only administrators can update rules. "
        "Changes take effect immediately for subsequent rule engine evaluations."
    ),
)
def update_rule(
    request: Request,
    rule_id: uuid.UUID,
    payload: RuleUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> RuleResponse:
    return RuleService(db).update_rule(
        rule_id=rule_id,
        payload=payload,
        updated_by=current_user,
        ip_address=get_client_ip(request),
        request_id=getattr(request.state, "request_id", "unknown"),
    )


# ---------------------------------------------------------------------------
# Toggle active status
# ---------------------------------------------------------------------------

@router.patch(
    "/{rule_id}/toggle",
    response_model=RuleResponse,
    status_code=status.HTTP_200_OK,
    summary="Activate or deactivate a rule",
    description=(
        "Soft-disables or re-enables a rule without deleting it. "
        "Inactive rules are not included in any evaluation run."
    ),
)
def toggle_rule(
    request: Request,
    rule_id: uuid.UUID,
    is_active: bool = Query(..., description="True to activate, False to deactivate"),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> RuleResponse:
    return RuleService(db).toggle_rule(
        rule_id=rule_id,
        is_active=is_active,
        updated_by=current_user,
        ip_address=get_client_ip(request),
        request_id=getattr(request.state, "request_id", "unknown"),
    )


# ---------------------------------------------------------------------------
# Delete rule
# ---------------------------------------------------------------------------

@router.delete(
    "/{rule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Permanently delete a rule",
    description=(
        "Hard-deletes a rule. Prefer PATCH /{rule_id}/toggle to deactivate instead. "
        "Deletion cannot be undone and is recorded in the audit log."
    ),
)
def delete_rule(
    request: Request,
    rule_id: uuid.UUID,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Response:
    RuleService(db).delete_rule(
        rule_id=rule_id,
        deleted_by=current_user,
        ip_address=get_client_ip(request),
        request_id=getattr(request.state, "request_id", "unknown"),
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Evaluate rules for an application
# ---------------------------------------------------------------------------

@router.post(
    "/evaluate/{application_id}",
    response_model=RuleEngineResponse,
    status_code=status.HTTP_200_OK,
    summary="Run the rule engine for an application",
    description=(
        "Evaluates all active banking rules against the application's calculated "
        "financial ratios. Returns a per-rule breakdown and an overall outcome:\n\n"
        "- **pass**: all rules cleared — ML prediction pipeline will proceed.\n"
        "- **manual_review**: one or more advisory rules triggered — loan flagged "
        "  for officer review, ML still runs.\n"
        "- **reject**: one or more mandatory rules failed — loan automatically rejected, "
        "  ML pipeline is skipped.\n\n"
        "Idempotent — re-running overwrites the stored evaluation result."
    ),
)
def evaluate_rules(
    request: Request,
    application_id: uuid.UUID,
    current_user: User = Depends(require_analyst),
    db: Session = Depends(get_db),
) -> RuleEngineResponse:
    return RuleService(db).evaluate_for_application(
        application_id=application_id,
        evaluated_by=current_user,
        ip_address=get_client_ip(request),
        request_id=getattr(request.state, "request_id", "unknown"),
    )


# ---------------------------------------------------------------------------
# Retrieve stored evaluation result
# ---------------------------------------------------------------------------

@router.get(
    "/evaluation/{application_id}",
    response_model=RuleEngineResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve the stored rule engine evaluation result",
    description=(
        "Returns the most recent rule engine evaluation result for the given application "
        "without re-running the evaluation. Raises 404 if evaluation has not been run yet."
    ),
)
def get_evaluation_result(
    application_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RuleEngineResponse:
    return RuleService(db).get_evaluation_result(application_id)
