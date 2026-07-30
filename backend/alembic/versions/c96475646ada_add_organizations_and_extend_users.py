"""add organizations and extend users

Revision ID: c96475646ada
Revises: 6e4544fb1cda
Create Date: 2026-07-21 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c96475646ada'
down_revision: Union[str, None] = '6e4544fb1cda'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('organizations',
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('slug', sa.String(length=255), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_organizations_id'), 'organizations', ['id'], unique=False)
    op.create_index(op.f('ix_organizations_name'), 'organizations', ['name'], unique=True)
    op.create_index(op.f('ix_organizations_slug'), 'organizations', ['slug'], unique=True)

    op.add_column('users', sa.Column('first_name', sa.String(length=128), nullable=True))
    op.add_column('users', sa.Column('last_name', sa.String(length=128), nullable=True))
    op.add_column('users', sa.Column('avatar_url', sa.String(length=1024), nullable=True))
    op.add_column('users', sa.Column('phone', sa.String(length=32), nullable=True))
    op.add_column('users', sa.Column('is_verified', sa.Boolean(), server_default=sa.text('false'), nullable=False))
    op.add_column('users', sa.Column('is_superadmin', sa.Boolean(), server_default=sa.text('false'), nullable=False))
    op.add_column('users', sa.Column('organization_id', sa.Integer(), nullable=True))
    op.add_column('users', sa.Column('failed_login_count', sa.Integer(), server_default=sa.text('0'), nullable=False))
    op.add_column('users', sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f('ix_users_organization_id'), 'users', ['organization_id'], unique=False)
    op.create_foreign_key(
        'fk_users_organization_id_organizations', 'users', 'organizations',
        ['organization_id'], ['id'], ondelete='SET NULL'
    )


def downgrade() -> None:
    op.drop_constraint('fk_users_organization_id_organizations', 'users', type_='foreignkey')
    op.drop_index(op.f('ix_users_organization_id'), table_name='users')
    op.drop_column('users', 'deleted_at')
    op.drop_column('users', 'last_login_at')
    op.drop_column('users', 'locked_until')
    op.drop_column('users', 'failed_login_count')
    op.drop_column('users', 'organization_id')
    op.drop_column('users', 'is_superadmin')
    op.drop_column('users', 'is_verified')
    op.drop_column('users', 'phone')
    op.drop_column('users', 'avatar_url')
    op.drop_column('users', 'last_name')
    op.drop_column('users', 'first_name')

    op.drop_index(op.f('ix_organizations_slug'), table_name='organizations')
    op.drop_index(op.f('ix_organizations_name'), table_name='organizations')
    op.drop_index(op.f('ix_organizations_id'), table_name='organizations')
    op.drop_table('organizations')
