"""seed roles and permissions

Revision ID: aa04beef73f6
Revises: 205d3a343582
Create Date: 2026-07-21 09:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.auth.permissions import ALL_PERMISSIONS, ROLE_NAMES, ROLE_PERMISSION_MATRIX


revision: str = 'aa04beef73f6'
down_revision: Union[str, None] = '205d3a343582'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    for name in ROLE_NAMES:
        conn.execute(
            sa.text(
                "INSERT INTO roles (name, description, created_at, updated_at) "
                "VALUES (:name, :description, now(), now()) "
                "ON CONFLICT (name) DO NOTHING"
            ),
            {"name": name, "description": f"{name} role"},
        )

    for code, description in ALL_PERMISSIONS:
        conn.execute(
            sa.text(
                "INSERT INTO permissions (code, description, created_at, updated_at) "
                "VALUES (:code, :description, now(), now()) "
                "ON CONFLICT (code) DO NOTHING"
            ),
            {"code": code, "description": description},
        )

    for role_name, permission_codes in ROLE_PERMISSION_MATRIX.items():
        for code in permission_codes:
            conn.execute(
                sa.text(
                    "INSERT INTO role_permissions (role_id, permission_id) "
                    "SELECT r.id, p.id FROM roles r, permissions p "
                    "WHERE r.name = :role_name AND p.code = :code "
                    "ON CONFLICT DO NOTHING"
                ),
                {"role_name": role_name, "code": code},
            )


def downgrade() -> None:
    conn = op.get_bind()

    role_names = list(ROLE_PERMISSION_MATRIX.keys())
    permission_codes = [code for code, _ in ALL_PERMISSIONS]

    conn.execute(
        sa.text(
            "DELETE FROM role_permissions WHERE role_id IN "
            "(SELECT id FROM roles WHERE name = ANY(:role_names)) "
            "OR permission_id IN (SELECT id FROM permissions WHERE code = ANY(:codes))"
        ),
        {"role_names": role_names, "codes": permission_codes},
    )
    conn.execute(
        sa.text("DELETE FROM permissions WHERE code = ANY(:codes)"),
        {"codes": permission_codes},
    )
    conn.execute(
        sa.text("DELETE FROM roles WHERE name = ANY(:role_names)"),
        {"role_names": role_names},
    )
