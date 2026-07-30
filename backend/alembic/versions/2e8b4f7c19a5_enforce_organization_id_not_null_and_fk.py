"""enforce organization_id not null and fk

Revision ID: 2e8b4f7c19a5
Revises: 9a5f13d8e6c2
Create Date: 2026-07-21 10:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '2e8b4f7c19a5'
down_revision: Union[str, None] = '9a5f13d8e6c2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CONTENT_TABLES = [
    'monitored_folders',
    'indexed_files',
    'file_chunks',
    'file_summaries',
    'file_tags',
    'document_entities',
    'search_query_logs',
]


def upgrade() -> None:
    for table in CONTENT_TABLES:
        op.alter_column(table, 'organization_id', existing_type=sa.Integer(), nullable=False)
        op.create_foreign_key(
            f'fk_{table}_organization_id_organizations', table, 'organizations',
            ['organization_id'], ['id'], ondelete='CASCADE'
        )


def downgrade() -> None:
    for table in reversed(CONTENT_TABLES):
        op.drop_constraint(f'fk_{table}_organization_id_organizations', table, type_='foreignkey')
        op.alter_column(table, 'organization_id', existing_type=sa.Integer(), nullable=True)
