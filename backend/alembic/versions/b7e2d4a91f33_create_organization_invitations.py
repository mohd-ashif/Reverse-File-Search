"""create organization invitations

Revision ID: b7e2d4a91f33
Revises: f3a1c9d2e765
Create Date: 2026-07-21 10:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b7e2d4a91f33'
down_revision: Union[str, None] = 'f3a1c9d2e765'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('organization_invitations',
    sa.Column('organization_id', sa.Integer(), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('role_id', sa.Integer(), nullable=False),
    sa.Column('token_hash', sa.String(length=64), nullable=False),
    sa.Column('status', sa.Enum('pending', 'accepted', 'expired', 'revoked', name='invitation_status'), server_default='pending', nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_by', sa.Integer(), nullable=True),
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_organization_invitations_id'), 'organization_invitations', ['id'], unique=False)
    op.create_index(op.f('ix_organization_invitations_organization_id'), 'organization_invitations', ['organization_id'], unique=False)
    op.create_index(op.f('ix_organization_invitations_email'), 'organization_invitations', ['email'], unique=False)
    op.create_index(op.f('ix_organization_invitations_token_hash'), 'organization_invitations', ['token_hash'], unique=True)
    op.create_index(
        'uq_org_invitations_pending_per_email',
        'organization_invitations',
        ['organization_id', 'email'],
        unique=True,
        postgresql_where=sa.text("status = 'pending'"),
    )


def downgrade() -> None:
    op.drop_index('uq_org_invitations_pending_per_email', table_name='organization_invitations')
    op.drop_index(op.f('ix_organization_invitations_token_hash'), table_name='organization_invitations')
    op.drop_index(op.f('ix_organization_invitations_email'), table_name='organization_invitations')
    op.drop_index(op.f('ix_organization_invitations_organization_id'), table_name='organization_invitations')
    op.drop_index(op.f('ix_organization_invitations_id'), table_name='organization_invitations')
    op.drop_table('organization_invitations')
