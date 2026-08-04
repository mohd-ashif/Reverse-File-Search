"""AuthService - orchestrates repositories + business logic for the auth flows.

Endpoints (a later phase) catch the exceptions defined here and translate them
into HTTP responses. Cookie-setting is an HTTP-layer concern and deliberately
kept out of this module: `login`/`refresh` return the raw refresh token plus
its expiry so the endpoint can call `response.set_cookie(...)` itself.
"""

import asyncio
import logging
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from fastapi import Request
from sqlalchemy.orm import Session

from app.auth.audit import AuditLogService, LoginHistoryService
from app.auth.jwt import TokenError, create_access_token, create_refresh_token, decode_token
from app.auth.mailer import send_login_alert_email, send_password_reset_email, send_verification_email
from app.auth.permissions import ALL_PERMISSIONS
from app.auth.repository import (
    EmailVerificationRepository,
    OrgRepository,
    PasswordResetRepository,
    RefreshTokenRepository,
    RoleRepository,
    SessionRepository,
    UserRepository,
)
from app.auth.security import hash_password, hash_token, verify_password
from app.core.config import settings
from app.models.organization import Organization, OrganizationMemberStatus, OrganizationInvitation, InvitationStatus
from app.models.user import User

logger = logging.getLogger(__name__)

__all__ = [
    "AuthError",
    "UserAlreadyExistsError",
    "InvalidCredentialsError",
    "AccountLockedError",
    "EmailNotVerifiedError",
    "InvalidTokenError",
    "InvitationError",
    "AuthTokenData",
    "AuthService",
]

EMAIL_VERIFICATION_EXPIRE_HOURS = 24
PASSWORD_RESET_EXPIRE_HOURS = 1
DEFAULT_SELF_REGISTER_ROLE = "Organization Admin"


class AuthError(Exception):
    """Base class for domain-level auth errors."""


class UserAlreadyExistsError(AuthError):
    pass


class InvalidCredentialsError(AuthError):
    pass


class AccountLockedError(AuthError):
    pass


class EmailNotVerifiedError(AuthError):
    pass


class InvalidTokenError(AuthError):
    pass


class InvitationError(AuthError):
    pass


@dataclass
class AuthTokenData:
    """Everything an endpoint needs to build a TokenResponse + set the refresh cookie."""

    user: User
    access_token: str
    refresh_token: str
    expires_in: int
    refresh_token_expires_at: datetime
    permissions: list[str]
    roles: list[str]
    organization: Organization | None


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)
        self.role_repo = RoleRepository(db)
        self.org_repo = OrgRepository(db)
        self.refresh_repo = RefreshTokenRepository(db)
        self.email_verification_repo = EmailVerificationRepository(db)
        self.password_reset_repo = PasswordResetRepository(db)
        self.session_repo = SessionRepository(db)
        self.audit_log = AuditLogService(db)
        self.login_history = LoginHistoryService(db)

    # -- registration / verification -------------------------------------------------

    def register(self, email: str, password: str, full_name: str | None = None) -> User:
        if self.user_repo.get_by_email(email) is not None:
            raise UserAlreadyExistsError(f"An account with email '{email}' already exists.")

        is_first_user = self.user_repo.count() == 0

        hashed = hash_password(password)
        user = self.user_repo.create(email=email, hashed_password=hashed, full_name=full_name)
        self.user_repo.update(user, is_verified=False)

        if is_first_user:
            org = self.org_repo.create_with_defaults(name="My Organization", is_platform_owner_org=True)
            self.user_repo.update(
                user, organization_id=org.id, is_superadmin=True, is_platform_owner=True
            )
            role = self.role_repo.assign_role_to_user(
                user_id=user.id, role_name="Super Admin", organization_id=org.id
            )
            self.org_repo.add_member(
                organization_id=org.id,
                user_id=user.id,
                role_id=role.role_id,
                status=OrganizationMemberStatus.OWNER,
                is_primary=True,
            )
            self.audit_log.log(
                user_id=user.id,
                organization_id=org.id,
                action="organization_created",
                resource_type="organization",
                resource_id=str(org.id),
            )
        else:
            # Every other self-registered user gets their own organization, so
            # their folders/files (both scoped by organization_id) are never
            # visible to any other user - each signup is its own isolated
            # tenant, not a shared workspace. Joining an existing org only
            # happens via an explicit invitation (see accept_invitation).
            org_name = f"{full_name or email}'s Organization"
            org = self.org_repo.create_with_defaults(name=org_name)
            self.user_repo.update(user, organization_id=org.id)
            role = self.role_repo.assign_role_to_user(
                user_id=user.id, role_name=DEFAULT_SELF_REGISTER_ROLE, organization_id=org.id
            )
            self.org_repo.add_member(
                organization_id=org.id,
                user_id=user.id,
                role_id=role.role_id,
                status=OrganizationMemberStatus.OWNER,
                is_primary=True,
            )
            self.audit_log.log(
                user_id=user.id,
                organization_id=org.id,
                action="organization_created",
                resource_type="organization",
                resource_id=str(org.id),
            )

        self.audit_log.log(user_id=user.id, organization_id=user.organization_id, action="user_registered")
        self._issue_and_send_verification(user)

        return user

    def accept_invitation(
        self, token_raw: str, password: str, full_name: str | None, request: Request | None = None
    ) -> AuthTokenData:
        from app.auth.mailer import send_org_join_email  # local import: avoid cycle at module load

        token_hash = hash_token(token_raw)
        invitation = (
            self.db.query(OrganizationInvitation)
            .filter(OrganizationInvitation.token_hash == token_hash)
            .first()
        )
        if invitation is None or invitation.status != InvitationStatus.PENDING:
            raise InvitationError("Invalid or already-used invitation.")
        if invitation.expires_at < datetime.now(timezone.utc):
            raise InvitationError("This invitation has expired.")

        user = self.user_repo.get_by_email(invitation.email)
        if user is None:
            hashed = hash_password(password)
            user = self.user_repo.create(email=invitation.email, hashed_password=hashed, full_name=full_name)
            self.user_repo.update(user, is_verified=True, organization_id=invitation.organization_id)
        elif user.organization_id is None:
            self.user_repo.update(user, organization_id=invitation.organization_id)

        self.role_repo.assign_role_to_user(
            user_id=user.id,
            role_name=self._role_name_by_id(invitation.role_id),
            organization_id=invitation.organization_id,
        )
        self.org_repo.add_member(
            organization_id=invitation.organization_id,
            user_id=user.id,
            role_id=invitation.role_id,
            status=OrganizationMemberStatus.JOINED,
            is_primary=user.organization_id == invitation.organization_id,
            invited_by=invitation.created_by,
        )

        invitation.status = InvitationStatus.ACCEPTED
        invitation.accepted_at = datetime.now(timezone.utc)
        self.db.commit()

        self.audit_log.log(
            user_id=user.id,
            organization_id=invitation.organization_id,
            action="invitation_accepted",
            resource_type="organization_invitation",
            resource_id=str(invitation.id),
            request=request,
        )

        org = self.org_repo.get_by_id(invitation.organization_id)
        self._best_effort_send(send_org_join_email, user.email, org.name if org else "")

        permissions, roles = self.get_permissions_and_roles(user)
        family_id = str(uuid.uuid4())
        ip_address = request.client.host if request is not None and request.client else None
        user_agent = request.headers.get("user-agent") if request is not None else None

        token_data = self._issue_token_pair(
            user=user, family_id=family_id, permissions=permissions, roles=roles,
            ip_address=ip_address, user_agent=user_agent,
        )
        self.session_repo.create(
            user_id=user.id, family_id=family_id, ip_address=ip_address, user_agent=user_agent
        )
        return token_data

    def _role_name_by_id(self, role_id: int) -> str:
        from app.models.role import Role

        role = self.db.get(Role, role_id)
        if role is None:
            raise InvitationError("Invited role no longer exists.")
        return role.name

    def _issue_and_send_verification(self, user: User) -> None:
        raw_token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=EMAIL_VERIFICATION_EXPIRE_HOURS)
        self.email_verification_repo.create(
            user_id=user.id, token_hash=hash_token(raw_token), expires_at=expires_at
        )
        self._best_effort_send(send_verification_email, user.email, raw_token)

    @staticmethod
    def _best_effort_send(coro_fn, *args) -> None:
        """Run an async mailer function to completion, swallowing any failure.

        Auth flows (registration, login, password reset) must not fail just
        because SMTP isn't configured yet. `AuthService` methods are sync and
        are called from FastAPI's sync-endpoint worker threads, which have no
        running event loop, so a plain `asyncio.run` is safe here.
        """
        try:
            asyncio.run(coro_fn(*args))
        except Exception:
            logger.warning("Best-effort email send failed", exc_info=True)

    def verify_email(self, token_raw: str) -> None:
        token_hash = hash_token(token_raw)
        row = self.email_verification_repo.get_valid_by_hash(token_hash)
        if row is None:
            raise InvalidTokenError("Invalid or expired verification token.")

        user = self.user_repo.get_by_id(row.user_id)
        if user is None:
            raise InvalidTokenError("Invalid or expired verification token.")

        self.user_repo.update(user, is_verified=True)
        self.email_verification_repo.mark_used(row)
        self.audit_log.log(
            user_id=user.id,
            organization_id=user.organization_id,
            action="email_verified",
        )

    def resend_verification(self, email: str) -> None:
        user = self.user_repo.get_by_email(email)
        if user is None or user.is_verified:
            return  # enumeration-avoidance: silent no-op either way

        self.email_verification_repo.invalidate_unused_for_user(user.id)
        self._issue_and_send_verification(user)

    # -- login / logout / refresh ------------------------------------------------------

    def login(self, email: str, password: str, request: Request | None = None) -> AuthTokenData:
        user = self.user_repo.get_by_email(email)
        if user is None:
            self.login_history.record(
                user_id=None, email_attempted=email, success=False,
                failure_reason="unknown_email", request=request,
            )
            raise InvalidCredentialsError("Invalid email or password.")

        now = datetime.now(timezone.utc)
        if user.locked_until is not None and user.locked_until > now:
            self.login_history.record(
                user_id=user.id, email_attempted=email, success=False,
                failure_reason="locked", request=request,
            )
            raise AccountLockedError("Account is temporarily locked due to too many failed login attempts.")

        if not user.is_active or user.deleted_at is not None:
            self.login_history.record(
                user_id=user.id, email_attempted=email, success=False,
                failure_reason="inactive", request=request,
            )
            raise InvalidCredentialsError("Invalid email or password.")

        if not verify_password(password, user.hashed_password):
            self.user_repo.increment_failed_login(user)
            if user.failed_login_count >= settings.MAX_FAILED_LOGIN_ATTEMPTS:
                self.user_repo.lock_account(
                    user, until=now + timedelta(minutes=settings.ACCOUNT_LOCKOUT_MINUTES)
                )
            self.login_history.record(
                user_id=user.id, email_attempted=email, success=False,
                failure_reason="bad_password", request=request,
            )
            raise InvalidCredentialsError("Invalid email or password.")

        if not user.is_verified:
            self.login_history.record(
                user_id=user.id, email_attempted=email, success=False,
                failure_reason="unverified", request=request,
            )
            raise EmailNotVerifiedError("Please verify your email address before logging in.")

        # success
        self.user_repo.reset_failed_login(user)
        self.user_repo.set_last_login(user, now)
        self.login_history.record(
            user_id=user.id, email_attempted=email, success=True, request=request
        )
        self.audit_log.log(
            user_id=user.id, organization_id=user.organization_id, action="login", request=request
        )

        permissions, roles = self.get_permissions_and_roles(user)

        family_id = str(uuid.uuid4())
        ip_address = request.client.host if request is not None and request.client else None
        user_agent = request.headers.get("user-agent") if request is not None else None

        token_data = self._issue_token_pair(
            user=user,
            family_id=family_id,
            permissions=permissions,
            roles=roles,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        self.session_repo.create(
            user_id=user.id, family_id=family_id, ip_address=ip_address, user_agent=user_agent
        )

        self._best_effort_send(send_login_alert_email, user.email, ip_address, user_agent)

        return token_data

    def _issue_token_pair(
        self,
        *,
        user: User,
        family_id: str,
        permissions: list[str],
        roles: list[str],
        ip_address: str | None,
        user_agent: str | None,
    ) -> AuthTokenData:
        access_token = create_access_token(
            user_id=user.id, org_id=user.organization_id, permissions=permissions, roles=roles
        )
        refresh_token, _jti, expires_at = create_refresh_token(user_id=user.id, family_id=family_id)

        self.refresh_repo.create(
            user_id=user.id,
            token_hash=hash_token(refresh_token),
            family_id=family_id,
            expires_at=expires_at,
            user_agent=user_agent,
            ip_address=ip_address,
        )

        return AuthTokenData(
            user=user,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            refresh_token_expires_at=expires_at,
            permissions=permissions,
            roles=roles,
            organization=user.organization,
        )

    def logout(self, refresh_token_raw: str | None) -> None:
        if not refresh_token_raw:
            return

        try:
            payload = decode_token(refresh_token_raw, expected_type="refresh")
        except TokenError:
            return

        token_hash = hash_token(refresh_token_raw)
        row = self.refresh_repo.get_by_hash(token_hash)
        if row is None:
            return

        self.refresh_repo.revoke_family(row.family_id)
        self.session_repo.revoke_by_family(row.family_id)

        user_id = payload.get("sub")
        if user_id is not None:
            try:
                user_id_int = int(user_id)
            except (TypeError, ValueError):
                user_id_int = None
            if user_id_int is not None:
                user = self.user_repo.get_by_id(user_id_int)
                self.audit_log.log(
                    user_id=user_id_int,
                    organization_id=user.organization_id if user else None,
                    action="logout",
                )

    def refresh(self, refresh_token_raw: str, request: Request | None = None) -> AuthTokenData:
        try:
            decode_token(refresh_token_raw, expected_type="refresh")
        except TokenError as exc:
            raise InvalidTokenError("Invalid or expired refresh token.") from exc

        token_hash = hash_token(refresh_token_raw)
        row = self.refresh_repo.get_by_hash(token_hash)
        if row is None:
            raise InvalidTokenError("Invalid or expired refresh token.")

        if row.revoked_at is not None:
            # Reuse of an already-rotated/revoked token - assume compromise, kill the family.
            self.refresh_repo.revoke_family(row.family_id)
            self.session_repo.revoke_by_family(row.family_id)
            self.audit_log.log(
                user_id=row.user_id,
                organization_id=None,
                action="refresh_token_reuse_detected",
                resource_type="refresh_token_family",
                resource_id=row.family_id,
                request=request,
            )
            raise InvalidTokenError("Refresh token has already been used; session revoked.")

        now = datetime.now(timezone.utc)
        expires_at = row.expires_at
        if expires_at.tzinfo is not None:
            now = datetime.now(timezone.utc)
        if expires_at < now:
            raise InvalidTokenError("Refresh token has expired.")

        user = self.user_repo.get_by_id(row.user_id)
        if user is None or not user.is_active or user.deleted_at is not None:
            raise InvalidTokenError("Invalid or expired refresh token.")

        # Rotate: revoke current row, issue a fresh one in the same family.
        self.refresh_repo.revoke(row)

        permissions, roles = self.get_permissions_and_roles(user)
        ip_address = request.client.host if request is not None and request.client else row.ip_address
        user_agent = request.headers.get("user-agent") if request is not None else row.user_agent

        token_data = self._issue_token_pair(
            user=user,
            family_id=row.family_id,
            permissions=permissions,
            roles=roles,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        new_row = self.refresh_repo.get_by_hash(hash_token(token_data.refresh_token))
        if new_row is not None:
            self.refresh_repo.mark_replaced(row, new_row)

        session_row = self.session_repo.get_by_family_id(row.family_id)
        if session_row is not None:
            self.session_repo.touch(session_row)

        return token_data

    # -- password management -------------------------------------------------------------

    def forgot_password(self, email: str) -> None:
        user = self.user_repo.get_by_email(email)
        if user is None:
            return  # enumeration-avoidance: silent no-op

        raw_token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=PASSWORD_RESET_EXPIRE_HOURS)
        self.password_reset_repo.create(
            user_id=user.id, token_hash=hash_token(raw_token), expires_at=expires_at
        )
        self._best_effort_send(send_password_reset_email, user.email, raw_token)

    def reset_password(self, token_raw: str, new_password: str) -> None:
        token_hash = hash_token(token_raw)
        row = self.password_reset_repo.get_valid_by_hash(token_hash)
        if row is None:
            raise InvalidTokenError("Invalid or expired reset token.")

        user = self.user_repo.get_by_id(row.user_id)
        if user is None:
            raise InvalidTokenError("Invalid or expired reset token.")

        self.user_repo.update(user, hashed_password=hash_password(new_password))
        self.password_reset_repo.mark_used(row)

        # Password reset should kill all existing sessions.
        active_sessions = self.session_repo.list_active_for_user(user.id)
        for session_row in active_sessions:
            self.refresh_repo.revoke_family(session_row.refresh_token_family_id)
            self.session_repo.revoke(session_row)

        self.audit_log.log(
            user_id=user.id, organization_id=user.organization_id, action="password_reset"
        )

    def change_password(self, user: User, current_password: str, new_password: str) -> None:
        if not verify_password(current_password, user.hashed_password):
            raise InvalidCredentialsError("Current password is incorrect.")

        self.user_repo.update(user, hashed_password=hash_password(new_password))
        self.audit_log.log(
            user_id=user.id, organization_id=user.organization_id, action="password_change"
        )

    # -- permissions -----------------------------------------------------------------------

    def get_permissions_and_roles(self, user: User) -> tuple[list[str], list[str]]:
        if user.is_superadmin:
            return [code for code, _ in ALL_PERMISSIONS], ["Super Admin"]

        role_names = self.role_repo.get_role_names_for_user(user.id, organization_id=user.organization_id)
        permissions = self.role_repo.get_permissions_for_roles(role_names)
        return permissions, role_names
