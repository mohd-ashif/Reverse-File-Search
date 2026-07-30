from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_permission
from app.auth.permissions import PermissionCode
from app.models.user import User
from app.schemas.organization import MemberRead, MemberRoleUpdateRequest, MemberUserRead
from app.services.organization_service import (
    CannotModifyOwnerError,
    InvalidRoleError,
    MemberNotFoundError,
    OrganizationService,
)

router = APIRouter()


def _member_to_read(member, db: Session) -> MemberRead:
    role_name = None
    if member.role_id is not None:
        from app.models.role import Role

        role = db.get(Role, member.role_id)
        role_name = role.name if role else None
    user = db.get(User, member.user_id)
    return MemberRead(
        id=member.id,
        user=MemberUserRead.model_validate(user),
        role=role_name,
        status=member.status.value,
        is_primary=member.is_primary,
        created_at=member.created_at,
    )


@router.patch("/{member_id}/role", response_model=MemberRead)
def change_member_role(
    member_id: int,
    payload: MemberRoleUpdateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(PermissionCode.ADMIN_ROLES)),
) -> MemberRead:
    try:
        member = OrganizationService(db).change_member_role(member_id, payload.role, actor=user)
    except MemberNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (InvalidRoleError, CannotModifyOwnerError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _member_to_read(member, db)


@router.delete("/{member_id}", status_code=204)
def remove_member(
    member_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(PermissionCode.ADMIN_USERS)),
) -> None:
    try:
        OrganizationService(db).remove_member(member_id, actor=user)
    except MemberNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except CannotModifyOwnerError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{member_id}/suspend", response_model=MemberRead)
def suspend_member(
    member_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(PermissionCode.ADMIN_USERS)),
) -> MemberRead:
    try:
        member = OrganizationService(db).suspend_member(member_id, actor=user)
    except MemberNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except CannotModifyOwnerError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _member_to_read(member, db)
