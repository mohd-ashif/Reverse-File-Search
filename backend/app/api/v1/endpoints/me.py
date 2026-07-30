from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.auth.repository import RefreshTokenRepository, SessionRepository, UserRepository
from app.auth.schemas import SessionRead, UserRead, UserUpdateRequest
from app.models.user import User

router = APIRouter()


@router.get("/", response_model=UserRead)
def get_me(user: User = Depends(get_current_user)) -> UserRead:
    return UserRead.model_validate(user)


@router.patch("/", response_model=UserRead)
def update_me(
    payload: UserUpdateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> UserRead:
    updated = UserRepository(db).update(user, **payload.model_dump(exclude_unset=True))
    return UserRead.model_validate(updated)


@router.get("/sessions", response_model=list[SessionRead])
def list_sessions(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[SessionRead]:
    # NOTE: the access token doesn't carry the refresh-token family_id, so
    # there's no reliable way to mark which session the current request
    # belongs to without adding that to the access token just for this
    # cosmetic feature. All active sessions are returned with
    # `is_current=False` (known limitation).
    sessions = SessionRepository(db).list_active_for_user(user.id)
    return [SessionRead.model_validate(s) for s in sessions]


@router.delete("/sessions/{session_id}", status_code=204)
def revoke_session(
    session_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    session_repo = SessionRepository(db)
    session_row = session_repo.get_by_id_for_user(session_id, user.id)
    if session_row is None:
        raise HTTPException(status_code=404, detail="Session not found.")

    RefreshTokenRepository(db).revoke_family(session_row.refresh_token_family_id)
    session_repo.revoke(session_row)
