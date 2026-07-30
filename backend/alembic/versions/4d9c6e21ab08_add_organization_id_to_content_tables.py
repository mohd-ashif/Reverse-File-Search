"""add organization_id to content tables

Revision ID: 4d9c6e21ab08
Revises: b7e2d4a91f33
Create Date: 2026-07-21 10:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '4d9c6e21ab08'
down_revision: Union[str, None] = 'b7e2d4a91f33'
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
        op.add_column(table, sa.Column('organization_id', sa.Integer(), nullable=True))
        op.create_index(f'ix_{table}_organization_id', table, ['organization_id'], unique=False)


def downgrade() -> None:
    for table in reversed(CONTENT_TABLES):
        op.drop_index(f'ix_{table}_organization_id', table_name=table)
        op.drop_column(table, 'organization_id')
