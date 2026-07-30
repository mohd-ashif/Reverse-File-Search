"""backfill organization_id content tables

Revision ID: 9a5f13d8e6c2
Revises: 4d9c6e21ab08
Create Date: 2026-07-21 10:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '9a5f13d8e6c2'
down_revision: Union[str, None] = '4d9c6e21ab08'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# All pre-existing rows in these tables predate the concept of an
# organization and cannot be attributed to any specific real org, so they
# are all backfilled onto the synthetic "Legacy Organization" created in
# f3a1c9d2e765.
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
    conn = op.get_bind()

    legacy_org_id = conn.execute(
        sa.text("SELECT id FROM organizations WHERE slug = 'legacy-organization'")
    ).scalar()

    if legacy_org_id is None:
        raise RuntimeError(
            "Legacy Organization row not found (slug='legacy-organization'); "
            "expected it to have been created by migration f3a1c9d2e765."
        )

    for table in CONTENT_TABLES:
        conn.execute(
            sa.text(f"UPDATE {table} SET organization_id = :legacy_id WHERE organization_id IS NULL"),
            {"legacy_id": legacy_org_id},
        )


def downgrade() -> None:
    conn = op.get_bind()

    legacy_org_id = conn.execute(
        sa.text("SELECT id FROM organizations WHERE slug = 'legacy-organization'")
    ).scalar()

    if legacy_org_id is None:
        return

    for table in reversed(CONTENT_TABLES):
        conn.execute(
            sa.text(f"UPDATE {table} SET organization_id = NULL WHERE organization_id = :legacy_id"),
            {"legacy_id": legacy_org_id},
        )
