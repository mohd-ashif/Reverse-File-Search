"""Bootstrap (or promote) a Super Admin user.

This is the operational entry point referenced by the auth/authz plan for
seeding the first privileged account after `alembic upgrade head` has run
(the seed migration inserts the 5 roles / 13 permissions, including the
"Super Admin" role assigned here).

Usage:
    python scripts/create_superadmin.py
    python scripts/create_superadmin.py --email admin@example.com --password "S0me!StrongPass" --full-name "Admin User"
    python scripts/create_superadmin.py --email existing@example.com --password "S0me!StrongPass" --promote

If --email/--password are omitted, the script falls back to interactive
prompts (email via input(), password via getpass so it is never echoed).

Behavior:
- New email                          -> creates a verified, active superadmin
                                         user and assigns the "Super Admin" role.
- Existing user, already superadmin   -> no-op, prints a message, exit 0.
- Existing user, not a superadmin     -> refuses (exit 1) unless --promote is
                                         passed, to avoid silently escalating
                                         an existing normal account.
- Existing user, not a superadmin,
  with --promote                      -> promotes the user in place and
                                         (re-)assigns the "Super Admin" role.
"""

import argparse
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.auth.password import PasswordPolicyError, validate_password_policy
from app.auth.repository import RoleRepository, UserRepository
from app.auth.security import hash_password
from app.db.session import SessionLocal


def _prompt_for_credentials(email: str | None, password: str | None) -> tuple[str, str]:
    if not email:
        email = input("Email: ").strip()
    if not password:
        password = getpass.getpass("Password: ")
    return email, password


def _ensure_super_admin_role_exists(role_repo: RoleRepository) -> None:
    if role_repo.get_by_name("Super Admin") is None:
        print(
            "Error: the 'Super Admin' role was not found in the database.\n"
            "Run 'alembic upgrade head' first to apply the RBAC seed migration, "
            "then re-run this script."
        )
        sys.exit(1)


def create_superadmin(email: str, password: str, full_name: str | None, promote: bool) -> None:
    email = email.strip()

    try:
        validate_password_policy(password)
    except PasswordPolicyError as exc:
        print("Error: password does not meet the required policy:")
        for violation in exc.violations:
            print(f"  - {violation}")
        sys.exit(1)

    db = SessionLocal()
    try:
        user_repo = UserRepository(db)
        role_repo = RoleRepository(db)

        _ensure_super_admin_role_exists(role_repo)

        existing = user_repo.get_by_email(email)

        if existing is not None:
            if existing.is_superadmin:
                print(f"User '{email}' (id={existing.id}) is already a Super Admin. Nothing to do.")
                sys.exit(0)

            if not promote:
                print(
                    f"Error: a user with email '{email}' already exists (id={existing.id}) "
                    "but is not a Super Admin.\n"
                    "Re-run with --promote to explicitly grant Super Admin privileges to this "
                    "existing account."
                )
                sys.exit(1)

            user = user_repo.update(
                existing,
                is_verified=True,
                is_superadmin=True,
                is_active=True,
            )
            action = "Promoted"
        else:
            user = user_repo.create(
                email=email,
                hashed_password=hash_password(password),
                full_name=full_name,
            )
            user = user_repo.update(
                user,
                is_verified=True,
                is_superadmin=True,
                is_active=True,
            )
            action = "Created"

        existing_roles = role_repo.get_role_names_for_user(user.id, organization_id=None)
        if "Super Admin" not in existing_roles:
            role_repo.assign_role_to_user(
                user_id=user.id,
                role_name="Super Admin",
                organization_id=None,
                granted_by=None,
            )

        print(f"{action} Super Admin user: email={user.email} id={user.id}")
    except SystemExit:
        raise
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--email", help="Email address of the Super Admin account (prompted if omitted)")
    parser.add_argument("--password", help="Password for the Super Admin account (prompted via getpass if omitted)")
    parser.add_argument("--full-name", default=None, help="Optional full name for a newly created user")
    parser.add_argument(
        "--promote",
        action="store_true",
        help="Allow promoting an existing non-superadmin user to Super Admin",
    )
    args = parser.parse_args()

    email, password = _prompt_for_credentials(args.email, args.password)
    create_superadmin(email=email, password=password, full_name=args.full_name, promote=args.promote)


if __name__ == "__main__":
    main()
