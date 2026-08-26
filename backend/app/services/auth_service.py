"""
AuthService — authentication and session management business logic.
All authentication decisions pass through this service; routes stay thin.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Any

from sqlalchemy.orm import Session

from app.config import settings
from app.core.exceptions import (
    AuthenticationError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from app.core.logging import get_logger
from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.models.audit_log import AuditAction
from app.models.user import User, UserRole, UserStatus
from app.repositories.audit_repository import AuditLogRepository
from app.repositories.user_repository import UserRepository
from app.models.company import Company, CompanyStatus, CompanyType, Industry
from app.repositories.company_repository import CompanyRepository
from app.schemas.auth import CompanyRegisterRequest, LoginRequest, PasswordChangeRequest, TokenResponse, TokenUserPayload
from app.schemas.user import UserCreate

logger = get_logger(__name__)


class AuthService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._user_repo = UserRepository(db)
        self._company_repo = CompanyRepository(db)
        self._audit_repo = AuditLogRepository(db)

    # -------------------------------------------------------------------------
    # Login
    # -------------------------------------------------------------------------

    def login(
        self,
        request: LoginRequest,
        ip_address: str = "unknown",
        user_agent: str = "unknown",
        request_id: str = "unknown",
    ) -> TokenResponse:
        """
        Authenticate a user and return a JWT token response.

        Raises:
            AuthenticationError: invalid credentials or inactive account.
        """
        user = self._user_repo.get_by_email(request.email)

        # Deliberate: same error for both "not found" and "wrong password"
        # to prevent email enumeration attacks.
        if not user or not verify_password(request.password, user.hashed_password):
            logger.warning(
                "Failed login attempt",
                extra={"email": request.email, "ip": ip_address},
            )
            # Audit the failure (user_id=None because we don't reveal who exists)
            self._audit_repo.log(
                action=AuditAction.USER_LOGIN,
                description=f"Failed login attempt for email: {request.email}",
                ip_address=ip_address,
                user_agent=user_agent,
                request_id=request_id,
            )
            raise AuthenticationError(message="Invalid email or password.")

        if user.status != UserStatus.ACTIVE:
            raise AuthenticationError(
                message=f"Account is {user.status.value}. Contact your administrator."
            )

        # Build token
        token = create_access_token(
            subject=str(user.id),
            extra_claims={
                "email": user.email,
                "role": user.role.value,
                "name": user.full_name,
            },
        )

        # Record last login
        now_str = datetime.now(timezone.utc).isoformat()
        self._user_repo.update_last_login(user, now_str)

        # Audit success
        self._audit_repo.log(
            action=AuditAction.USER_LOGIN,
            description=f"User {user.email} logged in successfully.",
            user_id=user.id,
            entity_type="user",
            entity_id=str(user.id),
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
        )

        logger.info("User logged in", extra={"user_id": str(user.id), "email": user.email})

        return TokenResponse(
            access_token=token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=TokenUserPayload.model_validate(user),
        )

    # -------------------------------------------------------------------------
    # Company self-registration (public)
    # -------------------------------------------------------------------------

    def register_company(
        self,
        request: CompanyRegisterRequest,
        ip_address: str = "unknown",
        user_agent: str = "unknown",
        request_id: str = "unknown",
    ) -> TokenResponse:
        if self._user_repo.exists_by_email(request.email):
            raise ConflictError(
                message=f"An account with email '{request.email}' already exists."
            )
        if self._company_repo.exists_by_registration_number(request.registration_number):
            raise ConflictError(
                message=f"A company with registration number '{request.registration_number}' is already registered."
            )

        company = self._company_repo.create(
            name=request.company_name.strip(),
            registration_number=request.registration_number.strip().upper(),
            company_type=CompanyType(request.company_type),
            industry=Industry(request.industry),
            status=CompanyStatus.UNDER_REVIEW,
            incorporation_date=request.incorporation_date,
            registered_address=request.registered_address,
            city=request.city,
            state=request.state,
            postal_code=request.postal_code,
            contact_email=request.email,
            contact_phone=request.contact_phone,
            website=request.website,
            annual_turnover=request.annual_turnover,
            number_of_employees=request.number_of_employees,
        )

        hashed = hash_password(request.password)
        user = self._user_repo.create(
            email=request.email,
            full_name=request.full_name,
            hashed_password=hashed,
            role=UserRole.COMPANY,
            department=None,
            phone=request.contact_phone,
            is_verified=True,
        )
        user.company_id = company.id
        self._db.flush()

        token = create_access_token(
            subject=str(user.id),
            extra_claims={
                "email": user.email,
                "role": user.role.value,
                "name": user.full_name,
            },
        )

        now_str = datetime.now(timezone.utc).isoformat()
        self._user_repo.update_last_login(user, now_str)

        self._audit_repo.log(
            action=AuditAction.USER_CREATED,
            description=f"Company '{company.name}' self-registered by {user.email}.",
            user_id=user.id,
            entity_type="company",
            entity_id=str(company.id),
            new_values={
                "company_name": company.name,
                "registration_number": company.registration_number,
                "industry": company.industry.value,
            },
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
        )

        logger.info(
            "Company self-registered",
            extra={"company_id": str(company.id), "user_id": str(user.id)},
        )

        return TokenResponse(
            access_token=token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=TokenUserPayload.model_validate(user),
        )

    # -------------------------------------------------------------------------
    # Register (admin-only action — called from UserService too)
    # -------------------------------------------------------------------------

    def register_user(
        self,
        data: UserCreate,
        created_by: User,
        ip_address: str = "unknown",
        request_id: str = "unknown",
    ) -> User:
        """
        Create a new user account.

        Raises:
            ConflictError: email already registered.
        """
        if self._user_repo.exists_by_email(data.email):
            raise ConflictError(
                message=f"An account with email '{data.email}' already exists."
            )

        hashed = hash_password(data.password)
        user = self._user_repo.create(
            email=data.email,
            full_name=data.full_name,
            hashed_password=hashed,
            role=data.role,
            department=data.department,
            phone=data.phone,
            profile_notes=data.profile_notes,
            is_verified=True,  # admin-created accounts are pre-verified
        )

        self._audit_repo.log(
            action=AuditAction.USER_CREATED,
            description=f"User {user.email} created by {created_by.email}.",
            user_id=created_by.id,
            entity_type="user",
            entity_id=str(user.id),
            new_values={"email": user.email, "role": user.role.value},
            ip_address=ip_address,
            request_id=request_id,
        )

        logger.info(
            "New user created",
            extra={
                "new_user_id": str(user.id),
                "created_by": str(created_by.id),
            },
        )
        return user

    # -------------------------------------------------------------------------
    # Change password
    # -------------------------------------------------------------------------

    def change_password(
        self,
        user: User,
        request: PasswordChangeRequest,
        ip_address: str = "unknown",
        request_id: str = "unknown",
    ) -> None:
        """
        Change the authenticated user's own password.

        Raises:
            AuthenticationError: current password incorrect.
        """
        if not verify_password(request.current_password, user.hashed_password):
            raise AuthenticationError(message="Current password is incorrect.")

        new_hash = hash_password(request.new_password)
        self._user_repo.update_password(user, new_hash)

        self._audit_repo.log(
            action=AuditAction.PASSWORD_CHANGED,
            description=f"Password changed for user {user.email}.",
            user_id=user.id,
            entity_type="user",
            entity_id=str(user.id),
            ip_address=ip_address,
            request_id=request_id,
        )

        logger.info("Password changed", extra={"user_id": str(user.id)})

    # -------------------------------------------------------------------------
    # Admin password reset
    # -------------------------------------------------------------------------

    def admin_reset_password(
        self,
        target_user: User,
        new_password: str,
        admin: User,
        ip_address: str = "unknown",
        request_id: str = "unknown",
    ) -> None:
        """Allow an admin to reset another user's password."""
        new_hash = hash_password(new_password)
        self._user_repo.update_password(target_user, new_hash)

        self._audit_repo.log(
            action=AuditAction.PASSWORD_CHANGED,
            description=f"Password reset for {target_user.email} by admin {admin.email}.",
            user_id=admin.id,
            entity_type="user",
            entity_id=str(target_user.id),
            ip_address=ip_address,
            request_id=request_id,
        )
