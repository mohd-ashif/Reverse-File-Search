import re
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.audit import UserSession
from app.models.auth_tokens import EmailVerification, PasswordResetToken
from app.models.organization import (
    InvitationStatus,
    Organization,
    OrganizationInvitation,
    OrganizationMemberStatus,
    OrganizationUser,
)
from app.models.refresh_token import RefreshToken
from app.models.role import Permission, Role, UserRole, role_permissions
from app.models.user import User


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: int) -> User | None:
        return self.db.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        return self.db.query(User).filter(User.email == email).first()

    def count(self) -> int:
        return self.db.query(User).count()

    def create(self, email: str, hashed_password: str, full_name: str | None = None) -> User:
        user = User(email=email, hashed_password=hashed_password, full_name=full_name)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def update(self, user: User, **fields) -> User:
        for key, value in fields.items():
            setattr(user, key, value)
        self.db.commit()
        self.db.refresh(user)
        return user

    def soft_delete(self, user: User) -> User:
        user.deleted_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(user)
        return user

    def increment_failed_login(self, user: User) -> User:
        user.failed_login_count += 1
        self.db.commit()
        self.db.refresh(user)
        return user

    def reset_failed_login(self, user: User) -> User:
        user.failed_login_count = 0
        self.db.commit()
        self.db.refresh(user)
        return user

    def lock_account(self, user: User, until: datetime) -> User:
        user.locked_until = until
        self.db.commit()
        self.db.refresh(user)
        return user

    def set_last_login(self, user: User, when: datetime) -> User:
        user.last_login_at = when
        self.db.commit()
        self.db.refresh(user)
        return user


class RoleRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_name(self, name: str) -> Role | None:
        return self.db.query(Role).filter(Role.name == name).first()

    def get_permissions_for_roles(self, role_names: list[str]) -> list[str]:
        if not role_names:
            return []
        rows = (
            self.db.query(Permission.code)
            .join(role_permissions, role_permissions.c.permission_id == Permission.id)
            .join(Role, Role.id == role_permissions.c.role_id)
            .filter(Role.name.in_(role_names))
            .distinct()
            .all()
        )
        return [code for (code,) in rows]

    def assign_role_to_user(
        self,
        user_id: int,
        role_name: str,
        organization_id: int | None = None,
        granted_by: int | None = None,
    ) -> UserRole:
        role = self.get_by_name(role_name)
        if role is None:
            raise ValueError(f"Role '{role_name}' does not exist")

        user_role = UserRole(
            user_id=user_id,
            role_id=role.id,
            organization_id=organization_id,
            granted_by=granted_by,
        )
        self.db.add(user_role)
        self.db.commit()
        self.db.refresh(user_role)
        return user_role

    def get_role_names_for_user(self, user_id: int, organization_id: int | None = None) -> list[str]:
        query = (
            self.db.query(Role.name)
            .join(UserRole, UserRole.role_id == Role.id)
            .filter(UserRole.user_id == user_id)
        )
        if organization_id is not None:
            query = query.filter(UserRole.organization_id == organization_id)
        rows = query.distinct().all()
        return [name for (name,) in rows]


class RefreshTokenRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        user_id: int,
        token_hash: str,
        family_id: str,
        expires_at: datetime,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> RefreshToken:
        row = RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            family_id=family_id,
            issued_at=datetime.now(timezone.utc),
            expires_at=expires_at,
            user_agent=user_agent,
            ip_address=ip_address,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        return self.db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()

    def revoke(self, token_row: RefreshToken) -> RefreshToken:
        token_row.revoked_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(token_row)
        return token_row

    def revoke_family(self, family_id: str) -> None:
        self.db.query(RefreshToken).filter(
            RefreshToken.family_id == family_id,
            RefreshToken.revoked_at.is_(None),
        ).update({"revoked_at": datetime.now(timezone.utc)}, synchronize_session=False)
        self.db.commit()

    def mark_replaced(self, old_row: RefreshToken, new_row: RefreshToken) -> RefreshToken:
        old_row.replaced_by_id = new_row.id
        self.db.commit()
        self.db.refresh(old_row)
        return old_row


class EmailVerificationRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, user_id: int, token_hash: str, expires_at: datetime) -> EmailVerification:
        row = EmailVerification(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def get_valid_by_hash(self, token_hash: str) -> EmailVerification | None:
        return (
            self.db.query(EmailVerification)
            .filter(
                EmailVerification.token_hash == token_hash,
                EmailVerification.used_at.is_(None),
                EmailVerification.expires_at > datetime.now(timezone.utc),
            )
            .first()
        )

    def mark_used(self, row: EmailVerification) -> EmailVerification:
        row.used_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(row)
        return row

    def invalidate_unused_for_user(self, user_id: int) -> None:
        self.db.query(EmailVerification).filter(
            EmailVerification.user_id == user_id,
            EmailVerification.used_at.is_(None),
        ).update({"used_at": datetime.now(timezone.utc)}, synchronize_session=False)
        self.db.commit()


class PasswordResetRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, user_id: int, token_hash: str, expires_at: datetime) -> PasswordResetToken:
        row = PasswordResetToken(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def get_valid_by_hash(self, token_hash: str) -> PasswordResetToken | None:
        return (
            self.db.query(PasswordResetToken)
            .filter(
                PasswordResetToken.token_hash == token_hash,
                PasswordResetToken.used_at.is_(None),
                PasswordResetToken.expires_at > datetime.now(timezone.utc),
            )
            .first()
        )

    def mark_used(self, row: PasswordResetToken) -> PasswordResetToken:
        row.used_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(row)
        return row


class OrgRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, organization_id: int) -> Organization | None:
        return self.db.get(Organization, organization_id)

    def create(self, name: str, slug: str) -> Organization:
        org = Organization(name=name, slug=slug)
        self.db.add(org)
        self.db.commit()
        self.db.refresh(org)
        return org

    def get_platform_owner_org(self) -> Organization | None:
        return self.db.query(Organization).filter(Organization.is_platform_owner_org.is_(True)).first()

    def _unique_slug(self, base_slug: str) -> str:
        slug = base_slug
        suffix = 1
        while self.db.query(Organization).filter(Organization.slug == slug).first() is not None:
            suffix += 1
            slug = f"{base_slug}-{suffix}"
        return slug

    def create_with_defaults(self, name: str, is_platform_owner_org: bool = False) -> Organization:
        base_slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "organization"
        org = Organization(
            name=name, slug=self._unique_slug(base_slug), is_platform_owner_org=is_platform_owner_org
        )
        self.db.add(org)
        self.db.commit()
        self.db.refresh(org)
        return org

    def add_member(
        self,
        organization_id: int,
        user_id: int,
        role_id: int | None,
        status: OrganizationMemberStatus,
        is_primary: bool = True,
        invited_by: int | None = None,
    ) -> OrganizationUser:
        member = OrganizationUser(
            organization_id=organization_id,
            user_id=user_id,
            role_id=role_id,
            status=status,
            is_primary=is_primary,
            invited_by=invited_by,
        )
        self.db.add(member)
        self.db.commit()
        self.db.refresh(member)
        return member


class OrganizationMemberRepository:
    """Queries over `OrganizationUser` / `OrganizationInvitation` for org admin flows."""

    def __init__(self, db: Session):
        self.db = db

    def list_orgs_for_user(self, user_id: int) -> list[Organization]:
        return (
            self.db.query(Organization)
            .join(OrganizationUser, OrganizationUser.organization_id == Organization.id)
            .filter(OrganizationUser.user_id == user_id)
            .all()
        )

    def get_membership(self, organization_id: int, user_id: int) -> OrganizationUser | None:
        return (
            self.db.query(OrganizationUser)
            .filter(
                OrganizationUser.organization_id == organization_id,
                OrganizationUser.user_id == user_id,
            )
            .first()
        )

    def get_member_by_id(self, member_id: int) -> OrganizationUser | None:
        return self.db.get(OrganizationUser, member_id)

    def list_members(self, organization_id: int) -> list[OrganizationUser]:
        return (
            self.db.query(OrganizationUser)
            .filter(OrganizationUser.organization_id == organization_id)
            .order_by(OrganizationUser.created_at.asc())
            .all()
        )

    def update_member(self, member: OrganizationUser, **fields) -> OrganizationUser:
        for key, value in fields.items():
            setattr(member, key, value)
        self.db.commit()
        self.db.refresh(member)
        return member

    def delete_member(self, member: OrganizationUser) -> None:
        self.db.delete(member)
        self.db.commit()

    def create_invitation(
        self,
        organization_id: int,
        email: str,
        role_id: int,
        token_hash: str,
        expires_at: datetime,
        created_by: int | None,
    ) -> OrganizationInvitation:
        row = OrganizationInvitation(
            organization_id=organization_id,
            email=email,
            role_id=role_id,
            token_hash=token_hash,
            expires_at=expires_at,
            created_by=created_by,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def get_pending_invitation(self, organization_id: int, email: str) -> OrganizationInvitation | None:
        return (
            self.db.query(OrganizationInvitation)
            .filter(
                OrganizationInvitation.organization_id == organization_id,
                OrganizationInvitation.email == email,
                OrganizationInvitation.status == InvitationStatus.PENDING,
            )
            .first()
        )

    def list_invitations(self, organization_id: int) -> list[OrganizationInvitation]:
        return (
            self.db.query(OrganizationInvitation)
            .filter(OrganizationInvitation.organization_id == organization_id)
            .order_by(OrganizationInvitation.created_at.desc())
            .all()
        )

    def get_invitation_by_id(self, invitation_id: int) -> OrganizationInvitation | None:
        return self.db.get(OrganizationInvitation, invitation_id)

    def update_invitation(self, invitation: OrganizationInvitation, **fields) -> OrganizationInvitation:
        for key, value in fields.items():
            setattr(invitation, key, value)
        self.db.commit()
        self.db.refresh(invitation)
        return invitation


class SessionRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        user_id: int,
        family_id: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> UserSession:
        row = UserSession(
            user_id=user_id,
            refresh_token_family_id=family_id,
            ip_address=ip_address,
            user_agent=user_agent,
            last_seen_at=datetime.now(timezone.utc),
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def list_active_for_user(self, user_id: int) -> list[UserSession]:
        return (
            self.db.query(UserSession)
            .filter(UserSession.user_id == user_id, UserSession.revoked_at.is_(None))
            .order_by(UserSession.created_at.desc())
            .all()
        )

    def get_by_id_for_user(self, session_id: int, user_id: int) -> UserSession | None:
        return (
            self.db.query(UserSession)
            .filter(UserSession.id == session_id, UserSession.user_id == user_id)
            .first()
        )

    def get_by_family_id(self, family_id: str) -> UserSession | None:
        return self.db.query(UserSession).filter(UserSession.refresh_token_family_id == family_id).first()

    def touch(self, session_row: UserSession) -> UserSession:
        session_row.last_seen_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(session_row)
        return session_row

    def revoke(self, session_row: UserSession) -> UserSession:
        session_row.revoked_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(session_row)
        return session_row

    def revoke_by_family(self, family_id: str) -> None:
        self.db.query(UserSession).filter(
            UserSession.refresh_token_family_id == family_id,
            UserSession.revoked_at.is_(None),
        ).update({"revoked_at": datetime.now(timezone.utc)}, synchronize_session=False)
        self.db.commit()
