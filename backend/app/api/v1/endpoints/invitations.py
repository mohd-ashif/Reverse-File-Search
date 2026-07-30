from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.auth.schemas import OrganizationRead, TokenResponse, UserRead
from app.auth.service import AuthService, AuthTokenData, InvitationError
from app.core.config import settings
from app.schemas.organization import AcceptInvitationRequest

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


@router.post("/accept", response_model=TokenResponse)
def accept_invitation(
    payload: AcceptInvitationRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> TokenResponse:
    try:
        token_data = AuthService(db).accept_invitation(
            token_raw=payload.token,
            password=payload.password,
            full_name=payload.full_name,
            request=request,
        )
    except InvitationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    _set_refresh_cookie(response, token_data)
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
