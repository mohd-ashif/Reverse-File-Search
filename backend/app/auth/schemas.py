from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator

from app.auth.password import PasswordPolicyError, validate_password_policy


def _validate_password(value: str) -> str:
    try:
        validate_password_policy(value)
    except PasswordPolicyError as exc:
        raise ValueError(" ".join(exc.violations)) from exc
    return value


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return _validate_password(value)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str | None = None


class OrganizationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    avatar_url: str | None = None
    phone: str | None = None
    is_active: bool
    is_verified: bool
    last_login_at: datetime | None = None
    created_at: datetime


class TokenResponse(BaseModel):
    accessToken: str
    refreshToken: str
    expiresIn: int
    user: UserRead
    permissions: list[str]
    roles: list[str] = []
    organization: OrganizationRead | None = None


class UserUpdateRequest(BaseModel):
    full_name: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    avatar_url: str | None = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        return _validate_password(value)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        return _validate_password(value)


class VerifyEmailRequest(BaseModel):
    token: str


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class SessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ip_address: str | None = None
    user_agent: str | None = None
    created_at: datetime
    last_seen_at: datetime
    is_current: bool = False


class MessageResponse(BaseModel):
    message: str
