from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator

from app.auth.password import PasswordPolicyError, validate_password_policy


def _validate_password(value: str) -> str:
    try:
        validate_password_policy(value)
    except PasswordPolicyError as exc:
        raise ValueError(" ".join(exc.violations)) from exc
    return value


class OrganizationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    is_active: bool
    logo_url: str | None = None
    website: str | None = None
    email: str | None = None
    phone: str | None = None
    country: str | None = None
    timezone: str
    industry: str | None = None
    subscription_plan: str
    storage_limit_bytes: int
    storage_used_bytes: int
    is_platform_owner_org: bool
    created_at: datetime
    updated_at: datetime


class OrganizationUpdateRequest(BaseModel):
    name: str | None = None
    logo_url: str | None = None
    website: str | None = None
    email: str | None = None
    phone: str | None = None
    country: str | None = None
    timezone: str | None = None
    industry: str | None = None
    storage_limit_bytes: int | None = None


class MemberUserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str | None = None
    avatar_url: str | None = None


class MemberRead(BaseModel):
    id: int
    user: MemberUserRead
    role: str | None
    status: str
    is_primary: bool
    created_at: datetime


class InviteMemberRequest(BaseModel):
    email: EmailStr
    role: str


class InvitationRead(BaseModel):
    id: int
    email: str
    role: str
    status: str
    expires_at: datetime
    accepted_at: datetime | None = None
    created_at: datetime


class MemberRoleUpdateRequest(BaseModel):
    role: str


class AcceptInvitationRequest(BaseModel):
    token: str
    password: str
    full_name: str | None = None

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return _validate_password(value)


class OrgSwitchResponse(BaseModel):
    accessToken: str
    refreshToken: str
    expiresIn: int
    permissions: list[str]
    roles: list[str]
    organization: OrganizationRead | None = None
