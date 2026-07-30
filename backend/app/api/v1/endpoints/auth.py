from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.auth.schemas import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    OrganizationRead,
    RefreshRequest,
    RegisterRequest,
    ResendVerificationRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserRead,
    VerifyEmailRequest,
)
from app.auth.service import (
    AccountLockedError,
    AuthService,
    AuthTokenData,
    EmailNotVerifiedError,
    InvalidCredentialsError,
    InvalidTokenError,
    UserAlreadyExistsError,
)
from app.auth.middleware import limiter
from app.core.config import settings
from app.models.user import User

router = APIRouter()


def _set_refresh_cookie(response: Response, token_data: AuthTokenData) -> None:
    response.set_cookie(
        key=settings.REFRESH_TOKEN_COOKIE_NAME,
        value=token_data.refresh_token,
        httponly=True,
        secure=settings.ENVIRONMENT == "production",
        samesite="lax",
        path=settings.REFRESH_TOKEN_COOKIE_PATH,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.REFRESH_TOKEN_COOKIE_NAME,
        path=settings.REFRESH_TOKEN_COOKIE_PATH,
    )


def _to_token_response(token_data: AuthTokenData) -> TokenResponse:
    return TokenResponse(
        accessToken=token_data.access_token,
        refreshToken=token_data.refresh_token,
        expiresIn=token_data.expires_in,
        user=UserRead.model_validate(token_data.user),
        permissions=token_data.permissions,
        roles=token_data.roles,
        organization=(
            OrganizationRead.model_validate(token_data.organization)
            if token_data.organization is not None
            else None
        ),
    )


def _get_incoming_refresh_token(request: Request, body_token: str | None) -> tuple[str | None, bool]:
    """Returns (raw_token, from_cookie)."""
    cookie_token = request.cookies.get(settings.REFRESH_TOKEN_COOKIE_NAME)
    if cookie_token:
        return cookie_token, True
    return body_token, False


@router.post("/register", response_model=MessageResponse, status_code=201)
@limiter.limit("3/minute")
def register(
    payload: RegisterRequest, request: Request, db: Session = Depends(get_db)
) -> MessageResponse:
    try:
        AuthService(db).register(
            email=payload.email, password=payload.password, full_name=payload.full_name
        )
    except UserAlreadyExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return MessageResponse(message="Registration successful. Please check your email to verify your account.")


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> TokenResponse:
    try:
        token_data = AuthService(db).login(
            email=payload.email, password=payload.password, request=request
        )
    except AccountLockedError as exc:
        raise HTTPException(status_code=423, detail=str(exc)) from exc
    except (InvalidCredentialsError, EmailNotVerifiedError) as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    _set_refresh_cookie(response, token_data)
    return _to_token_response(token_data)


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    request: Request,
    response: Response,
    payload: RefreshRequest | None = None,
    db: Session = Depends(get_db),
) -> TokenResponse:
    body_token = payload.refresh_token if payload is not None else None
    raw_token, from_cookie = _get_incoming_refresh_token(request, body_token)

    if not raw_token:
        raise HTTPException(status_code=401, detail="No refresh token provided.")

    if from_cookie and request.headers.get("X-Requested-With") != "XMLHttpRequest":
        raise HTTPException(
            status_code=403,
            detail="Missing required X-Requested-With header for cookie-based refresh.",
        )

    try:
        token_data = AuthService(db).refresh(raw_token, request=request)
    except InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    _set_refresh_cookie(response, token_data)
    return _to_token_response(token_data)


@router.post("/logout", response_model=MessageResponse)
def logout(
    request: Request,
    response: Response,
    payload: RefreshRequest | None = None,
    db: Session = Depends(get_db),
) -> MessageResponse:
    body_token = payload.refresh_token if payload is not None else None
    raw_token, _from_cookie = _get_incoming_refresh_token(request, body_token)

    AuthService(db).logout(raw_token)
    _clear_refresh_cookie(response)
    return MessageResponse(message="Logged out.")


@router.post("/verify-email", response_model=MessageResponse)
def verify_email(payload: VerifyEmailRequest, db: Session = Depends(get_db)) -> MessageResponse:
    try:
        AuthService(db).verify_email(payload.token)
    except InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    return MessageResponse(message="Email verified successfully.")


@router.post("/resend-verification", response_model=MessageResponse)
def resend_verification(
    payload: ResendVerificationRequest, db: Session = Depends(get_db)
) -> MessageResponse:
    AuthService(db).resend_verification(payload.email)
    return MessageResponse(message="If an account with that email exists, a verification email has been sent.")


@router.post("/forgot-password", response_model=MessageResponse)
@limiter.limit("3/minute")
def forgot_password(
    payload: ForgotPasswordRequest, request: Request, db: Session = Depends(get_db)
) -> MessageResponse:
    AuthService(db).forgot_password(payload.email)
    return MessageResponse(message="If an account with that email exists, a password reset email has been sent.")


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)) -> MessageResponse:
    try:
        AuthService(db).reset_password(payload.token, payload.new_password)
    except InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    return MessageResponse(message="Password has been reset. Please log in with your new password.")


@router.post("/change-password", response_model=MessageResponse)
def change_password(
    payload: ChangePasswordRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> MessageResponse:
    try:
        AuthService(db).change_password(user, payload.current_password, payload.new_password)
    except InvalidCredentialsError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    return MessageResponse(message="Password changed successfully.")
