"""Transactional email sending via fastapi-mail.

SMTP credentials are supplied later (per plan); until then `SMTP_HOST`
defaults to "localhost" with nothing listening, so send calls will fail at
runtime. Callers in app/auth/service.py treat these as best-effort and must
catch failures rather than let them propagate.
"""

from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType

from app.core.config import settings

conf = ConnectionConfig(
    MAIL_USERNAME=settings.SMTP_USERNAME,
    MAIL_PASSWORD=settings.SMTP_PASSWORD,
    MAIL_FROM=settings.SMTP_FROM_EMAIL,
    MAIL_FROM_NAME=settings.SMTP_FROM_NAME,
    MAIL_PORT=settings.SMTP_PORT,
    MAIL_SERVER=settings.SMTP_HOST,
    MAIL_STARTTLS=settings.SMTP_USE_TLS,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=bool(settings.SMTP_USERNAME),
    VALIDATE_CERTS=settings.SMTP_VALIDATE_CERTS,
)

fm = FastMail(conf)


async def send_verification_email(to_email: str, token: str) -> None:
    link = f"{settings.FRONTEND_BASE_URL}/verify-email?token={token}"
    message = MessageSchema(
        subject="Verify your email address",
        recipients=[to_email],
        body=(
            f"<p>Welcome to {settings.PROJECT_NAME}!</p>"
            f"<p>Please verify your email address by clicking the link below:</p>"
            f'<p><a href="{link}">{link}</a></p>'
            f"<p>This link expires in 24 hours.</p>"
        ),
        subtype=MessageType.html,
    )
    await fm.send_message(message)


async def send_password_reset_email(to_email: str, token: str) -> None:
    link = f"{settings.FRONTEND_BASE_URL}/reset-password?token={token}"
    message = MessageSchema(
        subject="Reset your password",
        recipients=[to_email],
        body=(
            f"<p>We received a request to reset your password.</p>"
            f"<p>Click the link below to choose a new password:</p>"
            f'<p><a href="{link}">{link}</a></p>'
            f"<p>This link expires in 1 hour. If you did not request this, you can ignore this email.</p>"
        ),
        subtype=MessageType.html,
    )
    await fm.send_message(message)


async def send_invitation_email(to_email: str, org_name: str, token: str, inviter_name: str) -> None:
    link = f"{settings.FRONTEND_BASE_URL}/invitations/accept?token={token}"
    message = MessageSchema(
        subject=f"You've been invited to join {org_name}",
        recipients=[to_email],
        body=(
            f"<p>{inviter_name} has invited you to join <strong>{org_name}</strong> on {settings.PROJECT_NAME}.</p>"
            f"<p>Click the link below to accept the invitation and set up your account:</p>"
            f'<p><a href="{link}">{link}</a></p>'
            f"<p>This invitation expires in 7 days.</p>"
        ),
        subtype=MessageType.html,
    )
    await fm.send_message(message)


async def send_org_join_email(to_email: str, org_name: str) -> None:
    message = MessageSchema(
        subject=f"Welcome to {org_name}",
        recipients=[to_email],
        body=(
            f"<p>You've successfully joined <strong>{org_name}</strong> on {settings.PROJECT_NAME}.</p>"
            f"<p>You can now sign in and get started.</p>"
        ),
        subtype=MessageType.html,
    )
    await fm.send_message(message)


async def send_role_changed_email(to_email: str, new_role: str) -> None:
    message = MessageSchema(
        subject="Your role has changed",
        recipients=[to_email],
        body=(
            f"<p>Your role has been updated to <strong>{new_role}</strong>.</p>"
            f"<p>If you have questions about this change, contact your organization admin.</p>"
        ),
        subtype=MessageType.html,
    )
    await fm.send_message(message)


async def send_login_alert_email(to_email: str, ip_address: str | None, user_agent: str | None) -> None:
    message = MessageSchema(
        subject="New login to your account",
        recipients=[to_email],
        body=(
            f"<p>Your account was just signed in to.</p>"
            f"<p>IP address: {ip_address or 'unknown'}</p>"
            f"<p>Device/browser: {user_agent or 'unknown'}</p>"
            f"<p>If this wasn't you, please reset your password immediately.</p>"
        ),
        subtype=MessageType.html,
    )
    await fm.send_message(message)
