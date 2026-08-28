"""
PipelineService — runs the full credit-assessment pipeline for an application.

Stage order (each stage gates the next):

    submit → OCR → ratios → rules → ML → report

Design notes
------------
* Every stage delegates to the same service the standalone endpoint uses, so
  behaviour, audit logging, and validation are identical to running the six
  calls by hand.
* Stages already complete are reported as ``skipped`` rather than re-run, which
  makes a pipeline run idempotent and safe to retry after a partial failure.
* The rule engine may legitimately terminate the pipeline early: a mandatory
  rule failure rejects the application and suppresses ML. That is a *successful*
  run with a ``skipped`` ML stage, not a failure.
* Each stage commits independently. A stage that raises leaves everything before
  it persisted, so a retry resumes rather than restarts.
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, NotFoundError
from app.core.logging import get_logger
from app.models.application import Application, ApplicationStatus, FinalDecision
from app.models.document import DocumentStatus
from app.models.user import User
from app.repositories.application_repository import ApplicationRepository
from app.repositories.document_repository import DocumentRepository
from app.repositories.report_repository import ReportRepository
from app.schemas.pipeline import (
    BatchPipelineItem,
    BatchPipelineResponse,
    PipelineRunResponse,
    PipelineStageState,
    PipelineStatusResponse,
    StageResult,
)
from app.services.application_service import ApplicationService
from app.services.ocr_service import OCRService
from app.services.prediction_service import PredictionService
from app.services.ratio_service import RatioService
from app.services.report_service import ReportService
from app.services.rule_service import RuleService

logger = get_logger(__name__)

# Stage keys in execution order, with the label shown in the UI.
STAGE_LABELS: List[Tuple[str, str]] = [
    ("submit", "Submit Application"),
    ("ocr", "OCR Extraction"),
    ("ratios", "Financial Ratios"),
    ("rules", "Rule Engine"),
    ("ml", "ML Prediction"),
    ("report", "Credit Report"),
]

_TERMINAL_DECISIONS = {FinalDecision.APPROVED, FinalDecision.REJECTED}


class PipelineService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._app_repo = ApplicationRepository(db)
        self._doc_repo = DocumentRepository(db)
        self._report_repo = ReportRepository(db)

        self._apps = ApplicationService(db)
        self._ocr = OCRService(db)
        self._ratios = RatioService(db)
        self._rules = RuleService(db)
        self._predictions = PredictionService(db)
        self._reports = ReportService(db)

    # =========================================================================
    # Status
    # =========================================================================

    def get_status(self, application_id: uuid.UUID) -> PipelineStatusResponse:
        app = self._load(application_id)
        docs = self._doc_repo.list_by_application(application_id)
        extracted = sum(1 for d in docs if d.status == DocumentStatus.EXTRACTED)
        p = app

        submitted = app.status != ApplicationStatus.DRAFT
        states: List[PipelineStageState] = [
            self._state("submit", "Submit Application", submitted,
                        can_run=not submitted and len(docs) > 0,
                        blocked="Upload at least one financial document." if not docs else None),
            self._state("ocr", "OCR Extraction", bool(p.ocr_completed),
                        can_run=len(docs) > 0 and not p.ocr_completed,
                        blocked="No documents uploaded." if not docs else None),
            self._state("ratios", "Financial Ratios", bool(p.ratios_calculated),
                        can_run=bool(p.ocr_completed) and not p.ratios_calculated,
                        blocked=None if p.ocr_completed else "OCR extraction must complete first."),
            self._state("rules", "Rule Engine", bool(p.rules_evaluated),
                        can_run=bool(p.ratios_calculated) and not p.rules_evaluated,
                        blocked=None if p.ratios_calculated else "Ratios must be calculated first."),
            self._state("ml", "ML Prediction", bool(p.ml_predicted),
                        can_run=bool(p.rules_evaluated) and not p.ml_predicted,
                        blocked=None if p.rules_evaluated else "Rules must be evaluated first."),
            self._state("report", "Credit Report", bool(p.report_generated),
                        can_run=bool(p.ratios_calculated),
                        blocked=None if p.ratios_calculated else "Ratios must be calculated first."),
        ]

        next_stage = next((s.stage for s in states if not s.complete), None)
        is_complete = all(s.complete for s in states)

        return PipelineStatusResponse(
            application_id=app.id,
            application_number=app.application_number,
            status=app.status.value,
            final_decision=app.final_decision.value,
            document_count=len(docs),
            documents_extracted=extracted,
            stages=states,
            next_stage=next_stage,
            is_complete=is_complete,
            can_run_pipeline=len(docs) > 0 and not is_complete,
        )

    @staticmethod
    def _state(stage: str, label: str, complete: bool, can_run: bool,
               blocked: Optional[str]) -> PipelineStageState:
        return PipelineStageState(
            stage=stage,
            label=label,
            complete=complete,
            can_run=can_run and not complete,
            blocked_reason=None if complete else blocked,
        )

    # =========================================================================
    # Full run
    # =========================================================================

    def run_full_pipeline(
        self,
        application_id: uuid.UUID,
        triggered_by: User,
        ip_address: str = "unknown",
        request_id: str = "unknown",
        generate_report: bool = True,
    ) -> PipelineRunResponse:
        """
        Execute every remaining stage in order.

        Raises:
            BadRequestError: if the application has no documents to work from.
        """
        app = self._load(application_id)
        docs = self._doc_repo.list_by_application(application_id)
        if not docs:
            raise BadRequestError(
                message=(
                    f"Application '{app.application_number}' has no documents attached. "
                    "Upload at least one financial document before running the pipeline."
                )
            )

        started = datetime.now(timezone.utc)
        run_start = time.perf_counter()
        stages: List[StageResult] = []
        failed_stage: Optional[str] = None

        logger.info(
            "Pipeline run starting",
            extra={"application_id": str(application_id), "user": triggered_by.email},
        )

        ctx = dict(ip_address=ip_address, request_id=request_id)

        # ── 1. Submit ────────────────────────────────────────────────────────
        stages.append(self._stage("submit", lambda: self._do_submit(app, triggered_by, ctx)))
        if not stages[-1].ok:
            failed_stage = "submit"

        # ── 2. OCR every document that has not been extracted ────────────────
        if failed_stage is None:
            stages.append(self._stage("ocr", lambda: self._do_ocr(application_id, triggered_by, ctx)))
            if not stages[-1].ok:
                failed_stage = "ocr"

        # ── 3. Ratios ────────────────────────────────────────────────────────
        if failed_stage is None:
            stages.append(self._stage("ratios", lambda: self._do_ratios(application_id, triggered_by, ctx)))
            if not stages[-1].ok:
                failed_stage = "ratios"

        # ── 4. Rules ─────────────────────────────────────────────────────────
        rule_outcome: Optional[str] = None
        ml_should_run = True
        if failed_stage is None:
            def _rules() -> str:
                nonlocal rule_outcome, ml_should_run
                res = self._rules.evaluate_for_application(
                    application_id=application_id, evaluated_by=triggered_by, **ctx
                )
                self._db.commit()
                rule_outcome = res.overall_outcome
                ml_should_run = res.ml_should_run
                return (
                    f"{len(res.passed_rules)}/{res.total_rules} rules passed; "
                    f"verdict '{res.overall_outcome}'"
                )
            stages.append(self._stage("rules", _rules))
            if not stages[-1].ok:
                failed_stage = "rules"

        # ── 5. ML — skipped when a mandatory rule already rejected ───────────
        ml_executed = False
        if failed_stage is None:
            if not ml_should_run:
                stages.append(StageResult(
                    stage="ml",
                    status="skipped",
                    detail="Mandatory rule failure rejected the application; ML prediction bypassed.",
                ))
            else:
                def _ml() -> str:
                    nonlocal ml_executed
                    res = self._predictions.predict_for_application(
                        application_id=application_id, predicted_by=triggered_by, **ctx
                    )
                    self._db.commit()
                    ml_executed = bool(res.ml_executed)
                    return (
                        f"{res.model_used} → PD {res.probability_of_default:.1%}, "
                        f"risk {res.risk_score:.1f} ({res.risk_level})"
                    )
                stages.append(self._stage("ml", _ml))
                if not stages[-1].ok:
                    failed_stage = "ml"

        # ── 6. Report ────────────────────────────────────────────────────────
        report_id: Optional[uuid.UUID] = None
        if failed_stage is None and generate_report:
            def _report() -> str:
                nonlocal report_id
                res = self._reports.generate_report(
                    application_id=application_id, generated_by=triggered_by, **ctx
                )
                self._db.commit()
                report_id = res.id
                return f"{res.filename} (v{res.version})"
            stages.append(self._stage("report", _report))
            if not stages[-1].ok:
                failed_stage = "report"
        elif not generate_report:
            stages.append(StageResult(
                stage="report", status="skipped",
                detail="Report generation not requested for this run.",
            ))

        # ── Assemble ─────────────────────────────────────────────────────────
        self._db.expire_all()
        final = self._load(application_id)
        duration = round(time.perf_counter() - run_start, 2)

        completed = sum(1 for s in stages if s.status == "completed")
        skipped = sum(1 for s in stages if s.status == "skipped")

        response = PipelineRunResponse(
            application_id=final.id,
            application_number=final.application_number,
            started_at=started.isoformat(),
            finished_at=datetime.now(timezone.utc).isoformat(),
            total_duration_seconds=duration,
            stages=stages,
            completed_stages=completed,
            skipped_stages=skipped,
            failed_stage=failed_stage,
            final_status=final.status.value,
            final_decision=final.final_decision.value,
            risk_score=float(final.risk_score) if final.risk_score is not None else None,
            risk_level=self._risk_level(final),
            rule_outcome=rule_outcome,
            ml_executed=ml_executed,
            report_id=report_id,
            summary=self._summarise(final, stages, failed_stage, duration),
        )

        logger.info(
            "Pipeline run finished",
            extra={
                "application_id": str(application_id),
                "duration_s": duration,
                "completed": completed,
                "skipped": skipped,
                "failed_stage": failed_stage or "none",
            },
        )
        return response

    # =========================================================================
    # Batch
    # =========================================================================

    def run_batch(
        self,
        application_ids: Optional[List[uuid.UUID]],
        triggered_by: User,
        limit: int = 25,
        ip_address: str = "unknown",
        request_id: str = "unknown",
    ) -> BatchPipelineResponse:
        """
        Run the pipeline for many applications.

        With no explicit ids, picks up every application that has documents but
        has not reached a final decision — the "process the backlog" case.
        """
        start = time.perf_counter()

        if application_ids:
            targets = [self._load(aid) for aid in application_ids]
        else:
            targets = self._find_pending(limit)

        items: List[BatchPipelineItem] = []
        succeeded = failed = skipped = 0

        for app in targets:
            try:
                result = self.run_full_pipeline(
                    application_id=app.id,
                    triggered_by=triggered_by,
                    ip_address=ip_address,
                    request_id=request_id,
                )
                if result.failed_stage:
                    failed += 1
                    items.append(BatchPipelineItem(
                        application_id=app.id, application_number=app.application_number,
                        status="failed",
                        detail=f"Stopped at '{result.failed_stage}'.",
                    ))
                else:
                    succeeded += 1
                    items.append(BatchPipelineItem(
                        application_id=app.id, application_number=app.application_number,
                        status="succeeded", detail=result.summary,
                    ))
            except BadRequestError as exc:
                skipped += 1
                items.append(BatchPipelineItem(
                    application_id=app.id, application_number=app.application_number,
                    status="skipped", detail=str(getattr(exc, "message", exc)),
                ))
            except Exception as exc:  # keep the batch going
                self._db.rollback()
                failed += 1
                logger.error(
                    "Batch pipeline item failed",
                    extra={"application_id": str(app.id), "error": str(exc)},
                )
                items.append(BatchPipelineItem(
                    application_id=app.id, application_number=app.application_number,
                    status="failed", detail=str(exc)[:300],
                ))

        return BatchPipelineResponse(
            requested=len(targets),
            succeeded=succeeded,
            failed=failed,
            skipped=skipped,
            items=items,
            duration_seconds=round(time.perf_counter() - start, 2),
        )

    def _find_pending(self, limit: int) -> List[Application]:
        """Applications with documents that have not reached a final decision."""
        return (
            self._db.query(Application)
            .filter(
                Application.final_decision.notin_(list(_TERMINAL_DECISIONS)),
                Application.status != ApplicationStatus.WITHDRAWN,
            )
            .order_by(Application.created_at.asc())
            .limit(limit)
            .all()
        )

    # =========================================================================
    # Stage implementations
    # =========================================================================

    def _do_submit(self, app: Application, user: User, ctx: dict) -> str:
        if app.status != ApplicationStatus.DRAFT:
            return "skip:already submitted"
        self._apps.submit_application(app_id=app.id, submitted_by=user, **ctx)
        self._db.commit()
        return "Application submitted for assessment."

    def _do_ocr(self, application_id: uuid.UUID, user: User, ctx: dict) -> str:
        docs = self._doc_repo.list_by_application(application_id)
        pending = [d for d in docs if d.status != DocumentStatus.EXTRACTED]

        if not pending:
            # All documents already extracted — make sure the application's
            # ocr_completed flag reflects that, so downstream stages can run.
            app = self._app_repo.get_by_id(application_id, load_company=False)
            if app and not app.ocr_completed and docs:
                top_level = [d for d in docs if d.parent_document_id is None]
                if top_level and all(d.status == DocumentStatus.EXTRACTED for d in top_level):
                    self._app_repo.mark_pipeline_stage(app, "ocr_completed")
                    self._db.commit()
            return f"skip:all {len(docs)} document(s) already extracted"

        extracted = 0
        for doc in pending:
            self._ocr.extract_document(document_id=doc.id, triggered_by=user, **ctx)
            extracted += 1
        self._db.commit()
        return f"Extracted {extracted} of {len(docs)} document(s)."

    def _do_ratios(self, application_id: uuid.UUID, user: User, ctx: dict) -> str:
        app = self._load(application_id)
        if app.ratios_calculated:
            return "skip:ratios already calculated"
        res = self._ratios.calculate_for_application(
            application_id=application_id, financial_year=None, calculated_by=user, **ctx
        )
        self._db.commit()
        count = len(getattr(res, "ratios", []) or [])
        return f"Calculated {count} financial ratios."

    # =========================================================================
    # Helpers
    # =========================================================================

    def _stage(self, name: str, fn) -> StageResult:
        """Run one stage, converting a ``skip:`` sentinel or exception into a result."""
        start = time.perf_counter()
        try:
            detail = fn()
            elapsed = round(time.perf_counter() - start, 2)
            if isinstance(detail, str) and detail.startswith("skip:"):
                return StageResult(
                    stage=name, status="skipped",
                    detail=detail[5:], duration_seconds=elapsed,
                )
            return StageResult(
                stage=name, status="completed",
                detail=detail, duration_seconds=elapsed,
            )
        except Exception as exc:
            self._db.rollback()
            elapsed = round(time.perf_counter() - start, 2)
            message = getattr(exc, "message", None) or str(exc)
            logger.error(
                "Pipeline stage failed",
                extra={"stage": name, "error": message},
            )
            return StageResult(
                stage=name, status="failed",
                detail=message[:400], duration_seconds=elapsed,
            )

    def _load(self, application_id: uuid.UUID) -> Application:
        app = self._app_repo.get_by_id(application_id)
        if not app:
            raise NotFoundError(message=f"Application '{application_id}' not found.")
        return app

    @staticmethod
    def _risk_level(app: Application) -> Optional[str]:
        pred = getattr(app, "prediction", None)
        if pred is not None and getattr(pred, "risk_level", None) is not None:
            level = pred.risk_level
            return level.value if hasattr(level, "value") else str(level)
        return None

    @staticmethod
    def _summarise(
        app: Application, stages: List[StageResult],
        failed_stage: Optional[str], duration: float,
    ) -> str:
        if failed_stage:
            detail = next((s.detail for s in stages if s.stage == failed_stage), "")
            return (
                f"Pipeline stopped at '{failed_stage}' after {duration}s. {detail or ''}".strip()
            )
        ran = sum(1 for s in stages if s.status == "completed")
        decision = app.final_decision.value.replace("_", " ")
        score = f" Risk score {float(app.risk_score):.1f}." if app.risk_score is not None else ""
        return (
            f"Pipeline completed {ran} stage(s) in {duration}s. "
            f"Application is now '{app.status.value.replace('_', ' ')}' "
            f"with decision '{decision}'.{score}"
        )
