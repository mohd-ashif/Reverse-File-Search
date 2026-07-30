"""grant admin.settings to Organization Admin

Revision ID: 7c1a9f4d2b6e
Revises: 2e8b4f7c19a5
Create Date: 2026-07-22 00:00:00.000000

Organization Admins manage their organization's settings (name, logo,
timezone, storage limits, etc. via PATCH /organizations/{id}) - per the
"Organization Admin: everything inside organization" permission matrix, this
was missing from the original seed migration's role_permissions grant.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '7c1a9f4d2b6e'
down_revision: Union[str, None] = '2e8b4f7c19a5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            "INSERT INTO role_permissions (role_id, permission_id) "
            "SELECT r.id, p.id FROM roles r, permissions p "
            "WHERE r.name = 'Organization Admin' AND p.code = 'admin.settings' "
            "ON CONFLICT DO NOTHING"
        )
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            "DELETE FROM role_permissions WHERE role_id IN "
            "(SELECT id FROM roles WHERE name = 'Organization Admin') "
            "AND permission_id IN (SELECT id FROM permissions WHERE code = 'admin.settings')"
        )
    )
