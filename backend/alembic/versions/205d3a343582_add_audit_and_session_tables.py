"""add audit and session tables

Revision ID: 205d3a343582
Revises: 966e0d770679
Create Date: 2026-07-21 09:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '205d3a343582'
down_revision: Union[str, None] = '966e0d770679'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('audit_logs',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('organization_id', sa.Integer(), nullable=True),
    sa.Column('action', sa.String(length=64), nullable=False),
    sa.Column('resource_type', sa.String(length=64), nullable=True),
    sa.Column('resource_id', sa.String(length=64), nullable=True),
    sa.Column('metadata_json', sa.JSON(), nullable=False),
    sa.Column('ip_address', sa.String(length=64), nullable=True),
    sa.Column('user_agent', sa.String(length=512), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_audit_logs_id'), 'audit_logs', ['id'], unique=False)
    op.create_index(op.f('ix_audit_logs_action'), 'audit_logs', ['action'], unique=False)
    op.create_index(op.f('ix_audit_logs_created_at'), 'audit_logs', ['created_at'], unique=False)

    op.create_table('login_history',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('email_attempted', sa.String(length=255), nullable=False),
    sa.Column('success', sa.Boolean(), nullable=False),
    sa.Column('failure_reason', sa.String(length=64), nullable=True),
    sa.Column('ip_address', sa.String(length=64), nullable=False),
    sa.Column('user_agent', sa.String(length=512), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_login_history_id'), 'login_history', ['id'], unique=False)
    op.create_index(op.f('ix_login_history_email_attempted'), 'login_history', ['email_attempted'], unique=False)
    op.create_index(op.f('ix_login_history_created_at'), 'login_history', ['created_at'], unique=False)

    op.create_table('user_sessions',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('refresh_token_family_id', sa.String(length=36), nullable=False),
    sa.Column('ip_address', sa.String(length=64), nullable=True),
    sa.Column('user_agent', sa.String(length=512), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_sessions_id'), 'user_sessions', ['id'], unique=False)
    op.create_index(
        op.f('ix_user_sessions_refresh_token_family_id'), 'user_sessions', ['refresh_token_family_id'], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_user_sessions_refresh_token_family_id'), table_name='user_sessions')
    op.drop_index(op.f('ix_user_sessions_id'), table_name='user_sessions')
    op.drop_table('user_sessions')

    op.drop_index(op.f('ix_login_history_created_at'), table_name='login_history')
    op.drop_index(op.f('ix_login_history_email_attempted'), table_name='login_history')
    op.drop_index(op.f('ix_login_history_id'), table_name='login_history')
    op.drop_table('login_history')

    op.drop_index(op.f('ix_audit_logs_created_at'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_action'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_id'), table_name='audit_logs')
    op.drop_table('audit_logs')
