"""phase3_query_responses

Adds the query_responses table for persisting AI Copilot responses (Phase 3).
Also adds Phase-3-specific performance indexes on normalized_facts for analytics queries.

Revision ID: 033193bbf483
Revises: 0002b
Create Date: 2026-09-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '033193bbf483'
down_revision: Union[str, None] = '0002b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── query_responses: persists every AI Copilot answer for audit ──────
    op.create_table(
        'query_responses',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('answer', sa.Text(), nullable=False),
        sa.Column('evidence', postgresql.JSONB(astext_type=sa.Text()), nullable=False,
                  server_default='[]'),
        sa.Column('conflicts_surfaced', postgresql.JSONB(astext_type=sa.Text()), nullable=False,
                  server_default='[]'),
        sa.Column('analytics_results', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('calculation', sa.Text(), nullable=True),
        sa.Column('confidence', sa.Integer(), nullable=False),
        sa.Column('reasoning_type', sa.String(length=30), nullable=False),
        sa.Column('intent_plan', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('model_used_intent', sa.String(length=100), nullable=True),
        sa.Column('model_used_synthesis', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    # Index for listing recent queries (common audit use-case)
    op.create_index('idx_query_responses_created_at', 'query_responses',
                    ['created_at'], unique=False)

    # ── Analytics performance indexes on normalized_facts ─────────────
    # These are needed for the Analytics Service's range queries.
    # Use IF NOT EXISTS–equivalent pattern: catch and ignore if already present.
    _try_create_index(
        'idx_nfacts_analytics',
        'normalized_facts',
        ['canonical_entity_id', 'metric', 'period_start', 'period_end'],
        postgresql_where=(
            "(canonical_entity_id IS NOT NULL AND metric IS NOT NULL "
            "AND period_start IS NOT NULL AND normalized_value IS NOT NULL)"
        ),
    )


def _try_create_index(name, table, columns, **kw):
    """Create index, silently skip if it already exists (idempotent)."""
    try:
        op.create_index(name, table, columns, **kw)
    except Exception:
        pass  # Index already exists from Phase 2 migration — safe to skip


def downgrade() -> None:
    op.drop_index('idx_query_responses_created_at', table_name='query_responses')
    op.drop_table('query_responses')
    try:
        op.drop_index('idx_nfacts_analytics', table_name='normalized_facts')
    except Exception:
        pass
