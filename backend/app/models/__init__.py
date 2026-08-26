"""
Import all models here so SQLAlchemy's mapper registry is fully populated
before Alembic or the app calls Base.metadata.create_all().
"""

from app.models.user import User, UserRole, UserStatus
from app.models.company import Company, CompanyType, CompanyStatus, Industry
from app.models.application import Application, ApplicationStatus, LoanPurpose, FinalDecision
from app.models.document import Document, DocumentType, DocumentStatus
from app.models.ocr_data import OCRData
from app.models.financial_ratio import FinancialRatio
from app.models.rule import Rule, RuleCategory, RuleAction, Operator
from app.models.prediction import Prediction, ModelUsed, PredictionOutcome, RiskLevel
from app.models.report import Report, ReportStatus
from app.models.audit_log import AuditLog, AuditAction

__all__ = [
    "User", "UserRole", "UserStatus",
    "Company", "CompanyType", "CompanyStatus", "Industry",
    "Application", "ApplicationStatus", "LoanPurpose", "FinalDecision",
    "Document", "DocumentType", "DocumentStatus",
    "OCRData",
    "FinancialRatio",
    "Rule", "RuleCategory", "RuleAction", "Operator",
    "Prediction", "ModelUsed", "PredictionOutcome", "RiskLevel",
    "Report", "ReportStatus",
    "AuditLog", "AuditAction",
]
