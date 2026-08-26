"""
RuleService — orchestrates rule CRUD and application-level rule evaluation.

Evaluation pipeline:
  1. Guard: application must have ratios calculated (rules need ratio values).
  2. Load all active rules ordered by priority.
  3. Load the latest FinancialRatio record (source of metric values).
  4. Call rules.engine.evaluate_rules() — stateless evaluator.
  5. Persist result in FinancialRatio.calculation_metadata["rule_evaluation"].
  6. If outcome == "reject": set Application.final_decision = REJECTED,
     set Application.decision_reason, set Application.status = REJECTED.
  7. If outcome == "manual_review": set Application.status = MANUAL_REVIEW.
  8. If outcome == "pass": set Application.status = RULE_EVALUATED.
  9. Always mark pipeline stage: rules_evaluated = True.
  10. Write audit log.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.core.logging import get_logger
from app.models.application import ApplicationStatus, FinalDecision
from app.models.audit_log import AuditAction
from app.models.financial_ratio import FinancialRatio
from app.models.rule import Rule, RuleCategory
from app.models.user import User
from app.repositories.application_repository import ApplicationRepository
from app.repositories.audit_repository import AuditLogRepository
from app.repositories.rule_repository import RuleRepository
from app.schemas.rule import (
    RuleCreate,
    RuleEngineResponse,
    RuleListResponse,
    RuleResponse,
    RuleResultItem,
    RuleUpdate,
)
from rules.engine import RuleEngineResult, evaluate_rules

logger = get_logger(__name__)


class RuleService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._repo = RuleRepository(db)
        self._app_repo = ApplicationRepository(db)
        self._audit = AuditLogRepository(db)

    # =========================================================================
    # CRUD
    # =========================================================================

    def list_rules(
        self,
        page: int = 1,
        page_size: int = 20,
        category: Optional[RuleCategory] = None,
        is_mandatory: Optional[bool] = None,
        is_active: Optional[bool] = None,
    ) -> RuleListResponse:
        items, total = self._repo.list(
            page=page,
            page_size=page_size,
            category=category,
            is_mandatory=is_mandatory,
            is_active=is_active,
        )
        total_pages = max(1, (total + page_size - 1) // page_size)
        return RuleListResponse(
            items=[RuleResponse.model_validate(r) for r in items],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    def get_rule(self, rule_id: uuid.UUID) -> RuleResponse:
        rule = self._repo.get_by_id(rule_id)
        if not rule:
            raise NotFoundError(message=f"Rule '{rule_id}' not found.")
        return RuleResponse.model_validate(rule)

    def create_rule(
        self,
        payload: RuleCreate,
        created_by: User,
        ip_address: str = "unknown",
        request_id: str = "unknown",
    ) -> RuleResponse:
        existing = self._repo.get_by_name(payload.name)
        if existing:
            raise ConflictError(
                message=f"A rule named '{payload.name}' already exists. "
                "Rule names must be unique. Update the existing rule or choose a different name."
            )

        rule = self._repo.create(**payload.model_dump())

        self._audit.log(
            action=AuditAction.RULE_CREATED,
            description=f"Banking rule '{rule.name}' created (category={rule.category.value}, mandatory={rule.is_mandatory}).",
            user_id=created_by.id,
            entity_type="rule",
            entity_id=str(rule.id),
            new_values={
                "name": rule.name,
                "category": rule.category.value,
                "metric_field": rule.metric_field,
                "operator": rule.operator.value,
                "threshold": float(rule.threshold) if rule.threshold is not None else None,
                "action": rule.action.value,
                "is_mandatory": rule.is_mandatory,
                "priority": rule.priority,
            },
            ip_address=ip_address,
            request_id=request_id,
        )
        logger.info("Rule created", extra={"rule_id": str(rule.id), "rule_name": rule.name})
        return RuleResponse.model_validate(rule)

    def update_rule(
        self,
        rule_id: uuid.UUID,
        payload: RuleUpdate,
        updated_by: User,
        ip_address: str = "unknown",
        request_id: str = "unknown",
    ) -> RuleResponse:
        rule = self._repo.get_by_id(rule_id)
        if not rule:
            raise NotFoundError(message=f"Rule '{rule_id}' not found.")

        if payload.name and payload.name != rule.name:
            clash = self._repo.get_by_name(payload.name)
            if clash and clash.id != rule_id:
                raise ConflictError(message=f"Another rule named '{payload.name}' already exists.")

        old_values = {
            "name": rule.name,
            "operator": rule.operator.value,
            "threshold": float(rule.threshold) if rule.threshold is not None else None,
            "is_mandatory": rule.is_mandatory,
            "is_active": rule.is_active,
            "priority": rule.priority,
        }

        update_data = {k: v for k, v in payload.model_dump(exclude_none=True).items()}
        self._repo.update(rule, **update_data)

        self._audit.log(
            action=AuditAction.RULE_UPDATED,
            description=f"Banking rule '{rule.name}' updated.",
            user_id=updated_by.id,
            entity_type="rule",
            entity_id=str(rule_id),
            old_values=old_values,
            new_values=update_data,
            ip_address=ip_address,
            request_id=request_id,
        )
        return RuleResponse.model_validate(rule)

    def toggle_rule(
        self,
        rule_id: uuid.UUID,
        is_active: bool,
        updated_by: User,
        ip_address: str = "unknown",
        request_id: str = "unknown",
    ) -> RuleResponse:
        rule = self._repo.get_by_id(rule_id)
        if not rule:
            raise NotFoundError(message=f"Rule '{rule_id}' not found.")

        self._repo.set_active(rule, is_active)
        action_str = "activated" if is_active else "deactivated"

        self._audit.log(
            action=AuditAction.RULE_UPDATED,
            description=f"Banking rule '{rule.name}' {action_str} by {updated_by.email}.",
            user_id=updated_by.id,
            entity_type="rule",
            entity_id=str(rule_id),
            old_values={"is_active": not is_active},
            new_values={"is_active": is_active},
            ip_address=ip_address,
            request_id=request_id,
        )
        return RuleResponse.model_validate(rule)

    def delete_rule(
        self,
        rule_id: uuid.UUID,
        deleted_by: User,
        ip_address: str = "unknown",
        request_id: str = "unknown",
    ) -> None:
        rule = self._repo.get_by_id(rule_id)
        if not rule:
            raise NotFoundError(message=f"Rule '{rule_id}' not found.")

        rule_name = rule.name
        self._repo.delete(rule)

        self._audit.log(
            action=AuditAction.RULE_DELETED,
            description=f"Banking rule '{rule_name}' permanently deleted by {deleted_by.email}.",
            user_id=deleted_by.id,
            entity_type="rule",
            entity_id=str(rule_id),
            ip_address=ip_address,
            request_id=request_id,
        )
        logger.warning("Rule deleted", extra={"rule_id": str(rule_id), "deleted_rule_name": rule_name})

    # =========================================================================
    # Evaluation
    # =========================================================================

    def evaluate_for_application(
        self,
        application_id: uuid.UUID,
        evaluated_by: User,
        ip_address: str = "unknown",
        request_id: str = "unknown",
    ) -> RuleEngineResponse:
        """
        Run all active rules against the application's computed ratios.
        Updates application status and decision based on the outcome.
        """
        # ── 1. Load application ───────────────────────────────────────────────
        app = self._app_repo.get_by_id(application_id)
        if not app:
            raise NotFoundError(message=f"Application '{application_id}' not found.")

        if not app.ratios_calculated:
            raise BadRequestError(
                message=(
                    f"Application '{app.application_number}' has not had financial ratios "
                    "calculated. Run ratio calculation before evaluating rules."
                )
            )

        # ── 2. Load active rules ──────────────────────────────────────────────
        rules: List[Rule] = self._repo.list_active_ordered()
        if not rules:
            raise BadRequestError(
                message="No active rules are configured in the system. "
                "An administrator must create at least one rule before evaluation can proceed."
            )

        # ── 3. Load latest ratio record ───────────────────────────────────────
        fr = self._get_latest_ratio(application_id)
        if not fr or not fr.ratios:
            raise BadRequestError(
                message=(
                    f"No ratio data found for application '{app.application_number}'. "
                    "Recalculate financial ratios before running the rule engine."
                )
            )

        # ── 4. Evaluate ───────────────────────────────────────────────────────
        engine_result: RuleEngineResult = evaluate_rules(rules, fr.ratios)

        # ── 5. Persist result in FinancialRatio.calculation_metadata ──────────
        metadata = dict(fr.calculation_metadata or {})
        metadata["rule_evaluation"] = engine_result.to_dict()
        metadata["rule_evaluation"]["evaluated_by"] = evaluated_by.email
        fr.calculation_metadata = metadata
        self._db.flush()

        # ── 6–8. Update application status and decision ───────────────────────
        self._apply_outcome(app, engine_result, evaluated_by.email)

        # ── 9. Mark pipeline stage ────────────────────────────────────────────
        self._app_repo.mark_pipeline_stage(app, "rules_evaluated")

        # ── 10. Audit log ─────────────────────────────────────────────────────
        self._audit.log(
            action=AuditAction.RULES_EVALUATED,
            description=(
                f"Rule engine evaluated {engine_result.total_rules} rules for "
                f"application '{app.application_number}'. "
                f"Outcome: {engine_result.overall_outcome}. "
                f"{engine_result.triggered_count} rule(s) triggered. "
                f"ML pipeline {'will' if engine_result.ml_should_run else 'will NOT'} run."
            ),
            user_id=evaluated_by.id,
            entity_type="application",
            entity_id=str(application_id),
            new_values={
                "overall_outcome": engine_result.overall_outcome,
                "ml_should_run": engine_result.ml_should_run,
                "triggered_count": engine_result.triggered_count,
                "mandatory_failures": engine_result.mandatory_failures,
                "advisory_triggers": engine_result.advisory_triggers,
            },
            ip_address=ip_address,
            request_id=request_id,
        )

        logger.info(
            "Rule evaluation complete",
            extra={
                "app_id": str(application_id),
                "outcome": engine_result.overall_outcome,
                "triggered": engine_result.triggered_count,
                "ml_runs": engine_result.ml_should_run,
            },
        )

        return self._build_response(application_id, engine_result)

    def get_evaluation_result(self, application_id: uuid.UUID) -> RuleEngineResponse:
        """Retrieve a previously stored evaluation result."""
        app = self._app_repo.get_by_id(application_id)
        if not app:
            raise NotFoundError(message=f"Application '{application_id}' not found.")

        fr = self._get_latest_ratio(application_id)
        if not fr:
            raise NotFoundError(
                message=f"No financial ratio record found for application '{application_id}'."
            )

        meta = fr.calculation_metadata or {}
        eval_data: Optional[Dict[str, Any]] = meta.get("rule_evaluation")
        if not eval_data:
            raise NotFoundError(
                message=(
                    f"No rule evaluation result found for application "
                    f"'{app.application_number}'. Run POST /rules/evaluate/{application_id} first."
                )
            )

        result = RuleEngineResult(
            overall_outcome=eval_data["overall_outcome"],
            ml_should_run=eval_data["ml_should_run"],
            evaluated_at=eval_data["evaluated_at"],
            total_rules=eval_data["total_rules"],
            triggered_count=eval_data["triggered_count"],
            mandatory_failures=eval_data.get("mandatory_failures", []),
            advisory_triggers=eval_data.get("advisory_triggers", []),
            passed_rules=eval_data.get("passed_rules", []),
            skipped_rules=eval_data.get("skipped_rules", []),
            results=[],
        )
        # Rebuild per-rule results
        from rules.engine import RuleResult
        for r in eval_data.get("results", []):
            result.results.append(
                RuleResult(
                    rule_id=r["rule_id"],
                    rule_name=r["rule_name"],
                    category=r["category"],
                    metric_field=r["metric_field"],
                    operator=r["operator"],
                    threshold=r.get("threshold"),
                    metric_value=r.get("metric_value"),
                    triggered=r["triggered"],
                    is_mandatory=r["is_mandatory"],
                    action=r["action"],
                    priority=r["priority"],
                    message=r["message"],
                )
            )
        return self._build_response(application_id, result)

    # =========================================================================
    # Private helpers
    # =========================================================================

    def _get_latest_ratio(self, application_id: uuid.UUID) -> Optional[FinancialRatio]:
        return (
            self._db.query(FinancialRatio)
            .filter(FinancialRatio.application_id == application_id)
            .order_by(FinancialRatio.created_at.desc())
            .first()
        )

    def _apply_outcome(
        self,
        app: Any,
        result: RuleEngineResult,
        evaluator_email: str,
    ) -> None:
        """Apply the engine outcome to the Application record."""
        if result.overall_outcome == "reject":
            failed_names = ", ".join(result.mandatory_failures[:5])
            if len(result.mandatory_failures) > 5:
                failed_names += f" and {len(result.mandatory_failures) - 5} more"
            reason = (
                f"Automatically rejected by the rule engine. "
                f"{len(result.mandatory_failures)} mandatory rule(s) failed: {failed_names}. "
                "The ML prediction pipeline was not executed."
            )
            self._app_repo.update(
                app,
                status=ApplicationStatus.REJECTED,
                final_decision=FinalDecision.REJECTED,
                decision_reason=reason,
            )

        elif result.overall_outcome == "manual_review":
            advisory_names = ", ".join(result.advisory_triggers[:5])
            reason = (
                f"Flagged for manual review by the rule engine. "
                f"{len(result.advisory_triggers)} advisory rule(s) triggered: {advisory_names}. "
                "The ML prediction pipeline will still run to assist the reviewing officer."
            )
            self._app_repo.update(
                app,
                status=ApplicationStatus.MANUAL_REVIEW,
                decision_reason=reason,
            )

        else:
            # outcome == "pass" — rules cleared, proceed to ML
            self._app_repo.update(
                app,
                status=ApplicationStatus.RULE_EVALUATED,
            )

    @staticmethod
    def _build_response(
        application_id: uuid.UUID,
        result: RuleEngineResult,
    ) -> RuleEngineResponse:
        rejection_reason: Optional[str] = None
        if result.overall_outcome == "reject" and result.mandatory_failures:
            rejection_reason = (
                f"The following mandatory rule(s) were violated: "
                + "; ".join(result.mandatory_failures)
                + ". Loan application has been automatically rejected."
            )

        return RuleEngineResponse(
            application_id=application_id,
            overall_outcome=result.overall_outcome,
            ml_should_run=result.ml_should_run,
            evaluated_at=result.evaluated_at,
            total_rules=result.total_rules,
            triggered_count=result.triggered_count,
            mandatory_failures=result.mandatory_failures,
            advisory_triggers=result.advisory_triggers,
            passed_rules=result.passed_rules,
            skipped_rules=result.skipped_rules,
            results=[
                RuleResultItem(
                    rule_id=r.rule_id,
                    rule_name=r.rule_name,
                    category=r.category,
                    metric_field=r.metric_field,
                    operator=r.operator,
                    threshold=r.threshold,
                    metric_value=r.metric_value,
                    triggered=r.triggered,
                    is_mandatory=r.is_mandatory,
                    action=r.action,
                    priority=r.priority,
                    message=r.message,
                )
                for r in result.results
            ],
            rejection_reason=rejection_reason,
        )
