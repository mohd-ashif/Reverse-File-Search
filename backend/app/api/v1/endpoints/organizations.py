from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_permission
from app.auth.jwt import create_access_token, create_refresh_token
from app.auth.permissions import PermissionCode
from app.auth.repository import OrganizationMemberRepository, RefreshTokenRepository, RoleRepository, SessionRepository
from app.auth.security import hash_token
from app.auth.service import AuthService
from app.core.config import settings
from app.models.user import User
from app.schemas.organization import (
    InvitationRead,
    InviteMemberRequest,
    MemberRead,
    MemberUserRead,
    OrganizationRead,
    OrganizationUpdateRequest,
    OrgSwitchResponse,
)
from app.services.organization_service import (
    InvalidRoleError,
    InvitationAlreadyPendingError,
    InvitationNotFoundError,
    OrganizationNotFoundError,
    OrganizationService,
)

router = APIRouter()


def _member_to_read(member, role_name: str | None, db: Session) -> MemberRead:
    user = db.get(User, member.user_id)
    return MemberRead(
        id=member.id,
        user=MemberUserRead.model_validate(user),
        role=role_name,
        status=member.status.value,
        is_primary=member.is_primary,
        created_at=member.created_at,
    )


def _invitation_to_read(invitation, role_name: str) -> InvitationRead:
    return InvitationRead(
        id=invitation.id,
        email=invitation.email,
        role=role_name,
        status=invitation.status.value,
        expires_at=invitation.expires_at,
        accepted_at=invitation.accepted_at,
        created_at=invitation.created_at,
    )


@router.get("/", response_model=list[OrganizationRead])
def list_organizations(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[OrganizationRead]:
    orgs = OrganizationService(db).list_organizations_for_user(user)
    return [OrganizationRead.model_validate(org) for org in orgs]


@router.patch("/{organization_id}", response_model=OrganizationRead)
def update_organization(
    organization_id: int,
    payload: OrganizationUpdateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(PermissionCode.ADMIN_SETTINGS)),
) -> OrganizationRead:
    try:
        org = OrganizationService(db).update_organization(
            organization_id, actor=user, **payload.model_dump(exclude_unset=True)
        )
    except OrganizationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return OrganizationRead.model_validate(org)


@router.get("/{organization_id}/members", response_model=list[MemberRead])
def list_members(
    organization_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(PermissionCode.ADMIN_USERS)),
) -> list[MemberRead]:
    role_repo = RoleRepository(db)
    members = OrganizationService(db).list_members(organization_id)
    result = []
    for member in members:
        role_name = _resolve_role_name(role_repo, member.role_id)
        result.append(_member_to_read(member, role_name, db))
    return result


def _resolve_role_name(role_repo: RoleRepository, role_id: int | None) -> str | None:
    if role_id is None:
        return None
    from app.models.role import Role

    role = role_repo.db.get(Role, role_id)
    return role.name if role else None


@router.post("/{organization_id}/invite", response_model=InvitationRead, status_code=201)
def invite_member(
    organization_id: int,
    payload: InviteMemberRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(PermissionCode.ADMIN_USERS)),
) -> InvitationRead:
    try:
        invitation, _raw_token = OrganizationService(db).invite_member(
            organization_id, email=payload.email, role_name=payload.role, invited_by=user
        )
    except InvalidRoleError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except InvitationAlreadyPendingError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _invitation_to_read(invitation, payload.role)


@router.get("/{organization_id}/invitations", response_model=list[InvitationRead])
def list_invitations(
    organization_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(PermissionCode.ADMIN_USERS)),
) -> list[InvitationRead]:
    role_repo = RoleRepository(db)
    invitations = OrganizationService(db).list_invitations(organization_id)
    return [
        _invitation_to_read(inv, _resolve_role_name(role_repo, inv.role_id) or "")
        for inv in invitations
    ]


@router.post("/{organization_id}/invitations/{invitation_id}/resend", response_model=InvitationRead)
def resend_invitation(
    organization_id: int,
    invitation_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(PermissionCode.ADMIN_USERS)),
) -> InvitationRead:
    service = OrganizationService(db)
    try:
        service.resend_invitation(invitation_id, actor=user)
    except InvitationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    invitation = service.member_repo.get_invitation_by_id(invitation_id)
    role_name = _resolve_role_name(RoleRepository(db), invitation.role_id) or ""
    return _invitation_to_read(invitation, role_name)


@router.delete("/{organization_id}/invitations/{invitation_id}", status_code=204)
def revoke_invitation(
    organization_id: int,
    invitation_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(PermissionCode.ADMIN_USERS)),
) -> None:
    try:
        OrganizationService(db).revoke_invitation(invitation_id, actor=user)
    except InvitationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{organization_id}/switch", response_model=OrgSwitchResponse)
def switch_organization(
    organization_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> OrgSwitchResponse:
    import uuid

    member_repo = OrganizationMemberRepository(db)
    membership = member_repo.get_membership(organization_id, user.id)
    if membership is None and not user.is_superadmin:
        raise HTTPException(status_code=403, detail="You are not a member of this organization.")

    auth_service = AuthService(db)
    auth_service.user_repo.update(user, organization_id=organization_id)
    permissions, roles = auth_service.get_permissions_and_roles(user)

    family_id = str(uuid.uuid4())
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    access_token = create_access_token(
        user_id=user.id, org_id=organization_id, permissions=permissions, roles=roles
    )
    refresh_token, _jti, expires_at = create_refresh_token(user_id=user.id, family_id=family_id)
    RefreshTokenRepository(db).create(
        user_id=user.id,
        token_hash=hash_token(refresh_token),
        family_id=family_id,
        expires_at=expires_at,
        user_agent=user_agent,
        ip_address=ip_address,
    )
    SessionRepository(db).create(user_id=user.id, family_id=family_id, ip_address=ip_address, user_agent=user_agent)

    org = OrganizationService(db).get_organization(organization_id)
    return OrgSwitchResponse(
        accessToken=access_token,
        refreshToken=refresh_token,
        expiresIn=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        permissions=permissions,
        roles=roles,
        organization=OrganizationRead.model_validate(org),
    )
