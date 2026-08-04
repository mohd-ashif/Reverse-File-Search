"""OrganizationService - business logic for org settings, membership, and invitations.

Mirrors `AuthService`'s repository-backed style (see app/auth/service.py):
endpoints catch the exceptions defined here and translate them to HTTP responses.
"""

import logging
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.auth.audit import AuditLogService
from app.auth.mailer import send_invitation_email, send_role_changed_email
from app.auth.permissions import ROLE_NAMES
from app.auth.repository import OrganizationMemberRepository, OrgRepository, RoleRepository, UserRepository
from app.auth.security import hash_token
from app.models.organization import InvitationStatus, Organization, OrganizationInvitation, OrganizationMemberStatus, OrganizationUser
from app.models.user import User

logger = logging.getLogger(__name__)

INVITATION_EXPIRE_DAYS = 7
NON_INVITABLE_ROLES = {"Super Admin"}


class OrganizationServiceError(Exception):
    """Base class for domain-level organization errors."""


class OrganizationNotFoundError(OrganizationServiceError):
    pass


class InvalidRoleError(OrganizationServiceError):
    pass


class InvitationAlreadyPendingError(OrganizationServiceError):
    pass


class InvitationNotFoundError(OrganizationServiceError):
    pass


class MemberNotFoundError(OrganizationServiceError):
    pass


class CannotModifyOwnerError(OrganizationServiceError):
    pass


class OrganizationService:
    def __init__(self, db: Session):
        self.db = db
        self.org_repo = OrgRepository(db)
        self.member_repo = OrganizationMemberRepository(db)
        self.role_repo = RoleRepository(db)
        self.user_repo = UserRepository(db)
        self.audit_log = AuditLogService(db)

    # -- organizations --------------------------------------------------------------------

    def list_organizations_for_user(self, user: User) -> list[Organization]:
        if user.is_superadmin:
            return self.db.query(Organization).order_by(Organization.created_at.asc()).all()
        return self.member_repo.list_orgs_for_user(user.id)

    def get_organization(self, organization_id: int) -> Organization:
        org = self.org_repo.get_by_id(organization_id)
        if org is None:
            raise OrganizationNotFoundError(f"Organization {organization_id} not found.")
        return org

    def update_organization(self, organization_id: int, actor: User, **fields) -> Organization:
        org = self.get_organization(organization_id)
        updates = {k: v for k, v in fields.items() if v is not None}
        for key, value in updates.items():
            setattr(org, key, value)
        self.db.commit()
        self.db.refresh(org)
        self.audit_log.log(
            user_id=actor.id,
            organization_id=org.id,
            action="settings_updated",
            resource_type="organization",
            resource_id=str(org.id),
            metadata={"fields": list(updates.keys())},
        )
        return org

    # -- members ----------------------------------------------------------------------------

    def list_members(self, organization_id: int) -> list[OrganizationUser]:
        return self.member_repo.list_members(organization_id)

    def change_member_role(self, member_id: int, new_role_name: str, actor: User) -> OrganizationUser:
        if new_role_name == "Super Admin":
            raise InvalidRoleError("Cannot assign the Super Admin role.")
        if new_role_name not in ROLE_NAMES:
            raise InvalidRoleError(f"Unknown role '{new_role_name}'.")

        member = self.member_repo.get_member_by_id(member_id)
        if member is None:
            raise MemberNotFoundError(f"Member {member_id} not found.")
        if member.status == OrganizationMemberStatus.OWNER and not actor.is_platform_owner:
            raise CannotModifyOwnerError("Only the platform owner can change the organization owner's role.")

        new_role = self.role_repo.get_by_name(new_role_name)
        if new_role is None:
            raise InvalidRoleError(f"Role '{new_role_name}' does not exist.")

        member = self.member_repo.update_member(member, role_id=new_role.id)

        # Keep the UserRole grant in sync so the JWT's `roles`/`perms` claims update
        # on the member's next login/refresh.
        existing_roles = self.role_repo.get_role_names_for_user(member.user_id, organization_id=member.organization_id)
        for role_name in existing_roles:
            if role_name != "Super Admin":
                self._revoke_role(member.user_id, role_name, member.organization_id)
        self.role_repo.assign_role_to_user(
            user_id=member.user_id, role_name=new_role_name, organization_id=member.organization_id
        )

        self.audit_log.log(
            user_id=actor.id,
            organization_id=member.organization_id,
            action="role_changed",
            resource_type="organization_member",
            resource_id=str(member.id),
            metadata={"new_role": new_role_name},
        )

        member_user = self.user_repo.get_by_id(member.user_id)
        if member_user is not None:
            self._best_effort_send(send_role_changed_email, member_user.email, new_role_name)

        return member

    def remove_member(self, member_id: int, actor: User) -> None:
        member = self.member_repo.get_member_by_id(member_id)
        if member is None:
            raise MemberNotFoundError(f"Member {member_id} not found.")
        if member.status == OrganizationMemberStatus.OWNER:
            raise CannotModifyOwnerError("The organization owner cannot be removed.")

        org_id, user_id = member.organization_id, member.user_id
        self.member_repo.delete_member(member)
        self.audit_log.log(
            user_id=actor.id,
            organization_id=org_id,
            action="member_removed",
            resource_type="organization_member",
            resource_id=str(member_id),
            metadata={"removed_user_id": user_id},
        )

    def suspend_member(self, member_id: int, actor: User) -> OrganizationUser:
        member = self.member_repo.get_member_by_id(member_id)
        if member is None:
            raise MemberNotFoundError(f"Member {member_id} not found.")
        if member.status == OrganizationMemberStatus.OWNER:
            raise CannotModifyOwnerError("The organization owner cannot be suspended.")

        member = self.member_repo.update_member(member, status=OrganizationMemberStatus.SUSPENDED)
        self.audit_log.log(
            user_id=actor.id,
            organization_id=member.organization_id,
            action="member_suspended",
            resource_type="organization_member",
            resource_id=str(member.id),
        )
        return member

    def _revoke_role(self, user_id: int, role_name: str, organization_id: int | None) -> None:
        from app.models.role import UserRole

        role = self.role_repo.get_by_name(role_name)
        if role is None:
            return
        self.db.query(UserRole).filter(
            UserRole.user_id == user_id,
            UserRole.role_id == role.id,
            UserRole.organization_id == organization_id,
        ).delete(synchronize_session=False)
        self.db.commit()

    # -- invitations ------------------------------------------------------------------------

    def list_invitations(self, organization_id: int) -> list[OrganizationInvitation]:
        return self.member_repo.list_invitations(organization_id)

    def invite_member(self, organization_id: int, email: str, role_name: str, invited_by: User) -> tuple[OrganizationInvitation, str]:
        if role_name in NON_INVITABLE_ROLES:
            raise InvalidRoleError("Cannot invite a member as Super Admin.")
        if role_name not in ROLE_NAMES:
            raise InvalidRoleError(f"Unknown role '{role_name}'.")

        role = self.role_repo.get_by_name(role_name)
        if role is None:
            raise InvalidRoleError(f"Role '{role_name}' does not exist.")

        if self.member_repo.get_pending_invitation(organization_id, email) is not None:
            raise InvitationAlreadyPendingError(f"An invitation is already pending for '{email}'.")

        raw_token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(days=INVITATION_EXPIRE_DAYS)
        invitation = self.member_repo.create_invitation(
            organization_id=organization_id,
            email=email,
            role_id=role.id,
            token_hash=hash_token(raw_token),
            expires_at=expires_at,
            created_by=invited_by.id,
        )

        org = self.get_organization(organization_id)
        self._best_effort_send(send_invitation_email, email, org.name, raw_token, invited_by.full_name or invited_by.email)

        self.audit_log.log(
            user_id=invited_by.id,
            organization_id=organization_id,
            action="invitation_sent",
            resource_type="organization_invitation",
            resource_id=str(invitation.id),
            metadata={"email": email, "role": role_name},
        )
        return invitation, raw_token

    def resend_invitation(self, invitation_id: int, actor: User) -> str:
        invitation = self.member_repo.get_invitation_by_id(invitation_id)
        if invitation is None or invitation.status != InvitationStatus.PENDING:
            raise InvitationNotFoundError(f"Invitation {invitation_id} not found or not pending.")

        raw_token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(days=INVITATION_EXPIRE_DAYS)
        self.member_repo.update_invitation(invitation, token_hash=hash_token(raw_token), expires_at=expires_at)

        org = self.get_organization(invitation.organization_id)
        self._best_effort_send(
            send_invitation_email, invitation.email, org.name, raw_token, actor.full_name or actor.email
        )
        return raw_token

    def revoke_invitation(self, invitation_id: int, actor: User) -> OrganizationInvitation:
        invitation = self.member_repo.get_invitation_by_id(invitation_id)
        if invitation is None:
            raise InvitationNotFoundError(f"Invitation {invitation_id} not found.")

        invitation = self.member_repo.update_invitation(invitation, status=InvitationStatus.REVOKED)
        self.audit_log.log(
            user_id=actor.id,
            organization_id=invitation.organization_id,
            action="invitation_revoked",
            resource_type="organization_invitation",
            resource_id=str(invitation.id),
        )
        return invitation

    @staticmethod
    def _best_effort_send(coro_fn, *args) -> None:
        import asyncio

        try:
            asyncio.run(coro_fn(*args))
        except Exception:
            logger.warning("Best-effort email send failed", exc_info=True)
