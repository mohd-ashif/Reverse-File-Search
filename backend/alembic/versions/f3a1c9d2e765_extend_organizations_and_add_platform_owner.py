"""extend organizations and add platform owner

Revision ID: f3a1c9d2e765
Revises: aa04beef73f6
Create Date: 2026-07-21 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'f3a1c9d2e765'
down_revision: Union[str, None] = 'aa04beef73f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

organization_member_status_enum = postgresql.ENUM(
    'invited', 'joined', 'suspended', 'owner',
    name='organization_member_status',
)


def upgrade() -> None:
    bind = op.get_bind()

    # organizations: additive profile/billing/limits columns
    op.add_column('organizations', sa.Column('logo_url', sa.String(length=1024), nullable=True))
    op.add_column('organizations', sa.Column('website', sa.String(length=512), nullable=True))
    op.add_column('organizations', sa.Column('email', sa.String(length=255), nullable=True))
    op.add_column('organizations', sa.Column('phone', sa.String(length=32), nullable=True))
    op.add_column('organizations', sa.Column('country', sa.String(length=64), nullable=True))
    op.add_column(
        'organizations',
        sa.Column('timezone', sa.String(length=64), server_default='UTC', nullable=False),
    )
    op.add_column('organizations', sa.Column('industry', sa.String(length=128), nullable=True))
    op.add_column(
        'organizations',
        sa.Column('subscription_plan', sa.String(length=32), server_default='free', nullable=False),
    )
    op.add_column(
        'organizations',
        sa.Column('storage_limit_bytes', sa.BigInteger(), server_default=sa.text('0'), nullable=False),
    )
    op.add_column(
        'organizations',
        sa.Column('storage_used_bytes', sa.BigInteger(), server_default=sa.text('0'), nullable=False),
    )
    op.add_column(
        'organizations',
        sa.Column('is_platform_owner_org', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    )

    # organization_users: role/status/invited_by
    organization_member_status_enum.create(bind, checkfirst=True)
    op.add_column(
        'organization_users',
        sa.Column('role_id', sa.Integer(), nullable=True),
    )
    op.add_column(
        'organization_users',
        sa.Column(
            'status',
            postgresql.ENUM(
                'invited', 'joined', 'suspended', 'owner',
                name='organization_member_status',
                create_type=False,
            ),
            server_default='joined',
            nullable=False,
        ),
    )
    op.add_column(
        'organization_users',
        sa.Column('invited_by', sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        'fk_organization_users_role_id_roles', 'organization_users', 'roles',
        ['role_id'], ['id'], ondelete='SET NULL'
    )
    op.create_foreign_key(
        'fk_organization_users_invited_by_users', 'organization_users', 'users',
        ['invited_by'], ['id'], ondelete='SET NULL'
    )

    # users: platform owner flag
    op.add_column(
        'users',
        sa.Column('is_platform_owner', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    )

    # Synthetic organization to own all pre-existing content rows once
    # organization_id becomes mandatory on content tables (see the
    # backfill migration). Idempotent: safe to run more than once.
    op.execute(
        sa.text(
            "INSERT INTO organizations "
            "(name, slug, is_active, timezone, subscription_plan, storage_limit_bytes, "
            "storage_used_bytes, is_platform_owner_org, created_at, updated_at) "
            "VALUES ('Legacy Organization', 'legacy-organization', true, 'UTC', 'free', 0, 0, false, now(), now()) "
            "ON CONFLICT (slug) DO NOTHING"
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM organizations WHERE slug = 'legacy-organization'"))

    op.drop_column('users', 'is_platform_owner')

    op.drop_constraint('fk_organization_users_invited_by_users', 'organization_users', type_='foreignkey')
    op.drop_constraint('fk_organization_users_role_id_roles', 'organization_users', type_='foreignkey')
    op.drop_column('organization_users', 'invited_by')
    op.drop_column('organization_users', 'status')
    op.drop_column('organization_users', 'role_id')
    organization_member_status_enum.drop(op.get_bind(), checkfirst=True)

    op.drop_column('organizations', 'is_platform_owner_org')
    op.drop_column('organizations', 'storage_used_bytes')
    op.drop_column('organizations', 'storage_limit_bytes')
    op.drop_column('organizations', 'subscription_plan')
    op.drop_column('organizations', 'industry')
    op.drop_column('organizations', 'timezone')
    op.drop_column('organizations', 'country')
    op.drop_column('organizations', 'phone')
    op.drop_column('organizations', 'email')
    op.drop_column('organizations', 'website')
    op.drop_column('organizations', 'logo_url')
