"""Lightweight audit-logging decorator for simple CRUD endpoints.

For auth-flow events with branching context (login success/failure, logout,
password change/reset) `AuthService` already calls `AuditLogService`/
`LoginHistoryService` directly - see `app/auth/audit.py`. This decorator is
only for the simple "endpoint succeeded -> write one audit row" case.
"""

import inspect
from functools import wraps
from typing import Callable, TypeVar

from app.auth.audit import AuditLogService
from app.models.user import User

F = TypeVar("F", bound=Callable)


def audit_action(action: str, resource_type: str | None = None) -> Callable[[F], F]:
    """Wraps a (sync) FastAPI endpoint function. After the wrapped function
    returns successfully, writes an `AuditLog` row using the `db` and
    `current_user` kwargs FastAPI injected into the call.

    Must be applied as the innermost decorator (closer to `def ...`) relative
    to `@router.get/post/...`, so FastAPI's route registration still sees the
    real endpoint signature. `functools.wraps` copies `__wrapped__`, and we
    additionally copy `__signature__` explicitly so FastAPI's dependency
    resolution is unaffected regardless of its `inspect.signature` handling.
    """

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            try:
                db = kwargs.get("db")
                current_user = kwargs.get("current_user")
                if current_user is None:
                    # Fallback: find any User instance among the injected kwargs,
                    # in case a decorated endpoint uses a different param name.
                    for value in kwargs.values():
                        if isinstance(value, User):
                            current_user = value
                            break
                request = kwargs.get("request")

                resource_id = None
                for key in ("folder_id", "file_id", "id"):
                    if key in kwargs:
                        resource_id = str(kwargs[key])
                        break

                if resource_id is None:
                    # Fallback for endpoints with no id-shaped kwarg (e.g. a
                    # POST "/" create route): pull it off the return value
                    # instead, since e.g. `add_folder` returns a `FolderRead`
                    # with an `id` field.
                    result_id = getattr(result, "id", None)
                    if result_id is not None:
                        resource_id = str(result_id)

                if db is not None and current_user is not None:
                    AuditLogService(db).log(
                        user_id=current_user.id,
                        organization_id=getattr(current_user, "organization_id", None),
                        action=action,
                        resource_type=resource_type,
                        resource_id=resource_id,
                        request=request,
                    )
            except Exception:  # noqa: BLE001 - audit logging must never break the actual request
                pass
            return result

        # Force FastAPI to see the original signature (params/types/dependencies)
        # rather than wrapper(*args, **kwargs), regardless of its own unwrapping.
        wrapper.__signature__ = inspect.signature(func)
        return wrapper  # type: ignore[return-value]

    return decorator
