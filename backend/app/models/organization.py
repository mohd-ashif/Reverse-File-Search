import enum
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import DateTime

from app.db.base_class import Base, TimestampMixin


class OrganizationMemberStatus(str, enum.Enum):
    INVITED = "invited"
    JOINED = "joined"
    SUSPENDED = "suspended"
    OWNER = "owner"


class InvitationStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    EXPIRED = "expired"
    REVOKED = "revoked"


class Organization(TimestampMixin, Base):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    logo_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    website: Mapped[str | None] = mapped_column(String(512), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    country: Mapped[str | None] = mapped_column(String(64), nullable=True)
    timezone: Mapped[str] = mapped_column(String(64), server_default="UTC", nullable=False)
    industry: Mapped[str | None] = mapped_column(String(128), nullable=True)
    subscription_plan: Mapped[str] = mapped_column(String(32), server_default="free", nullable=False)
    storage_limit_bytes: Mapped[int] = mapped_column(BigInteger, server_default="0", nullable=False)
    storage_used_bytes: Mapped[int] = mapped_column(BigInteger, server_default="0", nullable=False)
    is_platform_owner_org: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)

    users: Mapped[list["User"]] = relationship(back_populates="organization")


class OrganizationUser(TimestampMixin, Base):
    """Membership of a user in an organization."""

    __tablename__ = "organization_users"
    __table_args__ = (UniqueConstraint("organization_id", "user_id", name="uq_organization_users_org_id_user_id"),)

    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=True)
    role_id: Mapped[int | None] = mapped_column(ForeignKey("roles.id", ondelete="SET NULL"), nullable=True)
    status: Mapped[OrganizationMemberStatus] = mapped_column(
        Enum(
            OrganizationMemberStatus,
            name="organization_member_status",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        server_default="joined",
        nullable=False,
    )
    invited_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)


class OrganizationInvitation(TimestampMixin, Base):
    """A pending (or resolved) invitation for an email address to join an
    organization with a given role. Accepted via a one-time token."""

    __tablename__ = "organization_invitations"
    __table_args__ = (
        Index(
            "uq_org_invitations_pending_per_email",
            "organization_id",
            "email",
            unique=True,
            postgresql_where=text("status = 'pending'"),
        ),
    )

    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id", ondelete="RESTRICT"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    status: Mapped[InvitationStatus] = mapped_column(
        Enum(
            InvitationStatus,
            name="invitation_status",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        server_default="pending",
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
