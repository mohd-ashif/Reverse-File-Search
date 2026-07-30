from fastapi import Request
from sqlalchemy.orm import Session

from app.models.audit import AuditLog, LoginHistory


def _client_ip(request: Request | None) -> str | None:
    if request is None or request.client is None:
        return None
    return request.client.host


def _user_agent(request: Request | None) -> str | None:
    if request is None:
        return None
    return request.headers.get("user-agent")


class AuditLogService:
    def __init__(self, db: Session):
        self.db = db

    def log(
        self,
        *,
        user_id: int | None,
        organization_id: int | None,
        action: str,
        resource_type: str | None = None,
        resource_id: str | None = None,
        metadata: dict | None = None,
        request: Request | None = None,
    ) -> AuditLog:
        row = AuditLog(
            user_id=user_id,
            organization_id=organization_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            metadata_json=metadata or {},
            ip_address=_client_ip(request),
            user_agent=_user_agent(request),
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row


class LoginHistoryService:
    def __init__(self, db: Session):
        self.db = db

    def record(
        self,
        *,
        user_id: int | None,
        email_attempted: str,
        success: bool,
        failure_reason: str | None = None,
        request: Request | None = None,
    ) -> LoginHistory:
        row = LoginHistory(
            user_id=user_id,
            email_attempted=email_attempted,
            success=success,
            failure_reason=failure_reason,
            ip_address=_client_ip(request) or "unknown",
            user_agent=_user_agent(request),
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row
