"""Phase 5 schema migration.

Creates:
  users                  — JWT auth users
  parliamentary_queries  — parliamentary copilot with status FSM
  region_mapping         — entity → region geographic mapping (seeded below)
  forecast_results       — forecasting engine output
  benchmark_runs         — benchmark harness results
  benchmark_ground_truth — labeled ground truth for harness

Modifies:
  documents              — adds is_synthetic (bool), synthetic_type (text)

Seeds region_mapping with 24 reference-table entries for all canonical entities
from the Phase 2 seed. Source='reference_table' for all seeded rows.

Revision ID: 0005
Revises:     0004
Create Date: 2026-09-21
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB
from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004_phase4_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# ---------------------------------------------------------------------------
# Region mapping seed data
# Format: (canonical_name, entity_type, region_id, region_name, state_name, source_note)
# source = 'reference_table' for all rows — documented in source_note
# ---------------------------------------------------------------------------
_REGION_SEED = [
    ("Coal India Limited",         "subsidiary", "PAN", "Pan-India",          "Pan-India (HQ Kolkata)",
     "CIL is the holding company with operations across India; mapped to Pan-India region."),
    ("BCCL",                       "subsidiary", "JH",  "Jharkhand",          "Jharkhand",
     "BCCL operates in the Jharia coalfield, Jharkhand — reference table."),
    ("CCL",                        "subsidiary", "JH",  "Jharkhand",          "Jharkhand",
     "CCL is headquartered in Ranchi, Jharkhand — reference table."),
    ("ECL",                        "subsidiary", "WB",  "West Bengal",        "West Bengal",
     "ECL operates in the Raniganj coalfield, West Bengal — reference table."),
    ("WCL",                        "subsidiary", "MH",  "Maharashtra",        "Maharashtra",
     "WCL is headquartered in Nagpur, Maharashtra — reference table."),
    ("MCL",                        "subsidiary", "OD",  "Odisha",             "Odisha",
     "MCL operates in the Ib-valley and Talcher coalfields, Odisha — reference table."),
    ("NCL",                        "subsidiary", "MP",  "Madhya Pradesh",     "Madhya Pradesh",
     "NCL operates in the Singrauli coalfield, MP/UP border — assigned to MP as primary state."),
    ("SECL",                       "subsidiary", "CG",  "Chhattisgarh",       "Chhattisgarh",
     "SECL operates in Korba, Chhattisgarh — reference table."),
    ("NEC",                        "subsidiary", "AS",  "Assam",              "Assam",
     "NEC operates in Assam and Meghalaya — assigned to Assam as primary state."),
    ("CMPDI",                      "subsidiary", "JH",  "Jharkhand",          "Jharkhand",
     "CMPDI is headquartered in Ranchi, Jharkhand — reference table."),
    ("Moonidih Colliery",          "mine",       "JH",  "Jharkhand",          "Jharkhand",
     "Underground coking coal mine in Jharia coalfield, Jharkhand — reference table."),
    ("Jharia Division",            "mine",       "JH",  "Jharkhand",          "Jharkhand",
     "BCCL Jharia operational division, Jharkhand — reference table."),
    ("Sijua Area",                 "mine",       "JH",  "Jharkhand",          "Jharkhand",
     "BCCL Sijua area collieries, Jharia coalfield — reference table."),
    ("Katras Area",                "mine",       "JH",  "Jharkhand",          "Jharkhand",
     "BCCL Katras area collieries, Jharia coalfield — reference table."),
    ("Patherdih Colliery",         "mine",       "JH",  "Jharkhand",          "Jharkhand",
     "BCCL Patherdih colliery, Jharia coalfield — reference table."),
    ("Jharia Coalfield",           "coalfield",  "JH",  "Jharkhand",          "Jharkhand",
     "Premier coking coal reserve in Dhanbad district, Jharkhand — reference table."),
    ("Raniganj Coalfield",         "coalfield",  "WB",  "West Bengal",        "West Bengal",
     "Oldest coalfield in India, Bardhaman district, West Bengal — reference table."),
    ("Bokaro Coalfield",           "coalfield",  "JH",  "Jharkhand",          "Jharkhand",
     "Bokaro coalfield, Jharkhand — reference table."),
    ("North Karanpura Coalfield",  "coalfield",  "JH",  "Jharkhand",          "Jharkhand",
     "North Karanpura coalfield, Jharkhand — reference table."),
    ("Singrauli Coalfield",        "coalfield",  "MP",  "Madhya Pradesh",     "Madhya Pradesh",
     "Singrauli coalfield straddles MP/UP; assigned to MP — reference table."),
    ("Jharia Block A",             "location",   "JH",  "Jharkhand",          "Jharkhand",
     "Jharia coalfield survey block A — reference table."),
    ("Jharia Block B",             "location",   "JH",  "Jharkhand",          "Jharkhand",
     "Jharia coalfield survey block B — reference table."),
    ("Bokaro Site 1",              "location",   "JH",  "Jharkhand",          "Jharkhand",
     "Bokaro coalfield survey site 1 — reference table."),
    ("Raniganj East",              "location",   "WB",  "West Bengal",        "West Bengal",
     "Raniganj coalfield eastern section — reference table."),
]


def upgrade() -> None:

    # ------------------------------------------------------------------
    # 1. users
    # ------------------------------------------------------------------
    op.create_table(
        "users",
        sa.Column("id",              UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("username",        sa.String(150),     nullable=False, unique=True),
        sa.Column("hashed_password", sa.Text(),          nullable=False),
        sa.Column("role",            sa.String(20),      nullable=False, server_default="analyst"),
        sa.Column("is_active",       sa.Boolean(),       nullable=False, server_default="true"),
        sa.Column("created_at",      sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at",      sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.CheckConstraint("role IN ('analyst', 'reviewer', 'admin')", name="chk_user_role"),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    # ------------------------------------------------------------------
    # 2. parliamentary_queries
    # ------------------------------------------------------------------
    op.create_table(
        "parliamentary_queries",
        sa.Column("id",                   UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("question",             sa.Text(),          nullable=False),
        sa.Column("submitted_by_id",      UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("intent_plan",          JSONB,              nullable=True),
        sa.Column("evidence",             JSONB,              nullable=False, server_default=sa.text("'[]'")),
        sa.Column("conflicts_surfaced",   JSONB,              nullable=False, server_default=sa.text("'[]'")),
        sa.Column("analytics_results",    JSONB,              nullable=True),
        sa.Column("calculation",          sa.Text(),          nullable=True),
        sa.Column("confidence",           sa.Integer(),       nullable=True),
        sa.Column("reasoning_type",       sa.String(30),      nullable=True),
        sa.Column("has_open_conflicts",   sa.Boolean(),       nullable=False, server_default="false"),
        sa.Column("draft_answer",         sa.Text(),          nullable=True),
        sa.Column("status",               sa.String(20),      nullable=False, server_default="pending_review"),
        sa.Column("reviewer_id",          UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reviewer_note",        sa.Text(),          nullable=True),
        sa.Column("reviewed_at",          sa.DateTime(timezone=True), nullable=True),
        sa.Column("model_used_intent",    sa.String(100),     nullable=True),
        sa.Column("model_used_synthesis", sa.String(100),     nullable=True),
        sa.Column("created_at",           sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at",           sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.CheckConstraint(
            "status IN ('draft', 'pending_review', 'approved', 'rejected')",
            name="chk_parl_status",
        ),
    )
    op.create_index("ix_parl_status", "parliamentary_queries", ["status"])

    # ------------------------------------------------------------------
    # 3. region_mapping
    # ------------------------------------------------------------------
    op.create_table(
        "region_mapping",
        sa.Column("id",                  UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("canonical_entity_id", UUID(as_uuid=True), sa.ForeignKey("canonical_entities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("region_id",           sa.String(10),      nullable=False),
        sa.Column("region_name",         sa.String(100),     nullable=False),
        sa.Column("state_name",          sa.String(100),     nullable=False),
        sa.Column("source",              sa.String(20),      nullable=False, server_default="reference_table"),
        sa.Column("source_note",         sa.Text(),          nullable=True),
        sa.Column("created_at",          sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("canonical_entity_id", name="uq_region_entity"),
        sa.CheckConstraint("source IN ('reference_table', 'document_derived')", name="chk_region_source"),
    )
    op.create_index("ix_region_mapping_region_id", "region_mapping", ["region_id"])

    # ------------------------------------------------------------------
    # 4. forecast_results
    # ------------------------------------------------------------------
    op.create_table(
        "forecast_results",
        sa.Column("id",                    UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("entity_id",             UUID(as_uuid=True), sa.ForeignKey("canonical_entities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("metric",                sa.String(200),     nullable=False),
        sa.Column("horizon_years",         sa.Integer(),       nullable=False),
        sa.Column("model_used",            sa.String(50),      nullable=False),
        sa.Column("escalation_reason",     sa.Text(),          nullable=True),
        sa.Column("training_period_start", sa.Date(),          nullable=True),
        sa.Column("training_period_end",   sa.Date(),          nullable=True),
        sa.Column("training_data_points",  sa.Integer(),       nullable=False, server_default="0"),
        sa.Column("forecast_data",         JSONB,              nullable=False, server_default=sa.text("'{}'") ),
        sa.Column("data_quality_summary",  JSONB,              nullable=False, server_default=sa.text("'{}'") ),
        sa.Column("forecast_type",         sa.String(50),      nullable=False, server_default=sa.text("'Model-based forecast'")),
        sa.Column("insufficient_data",     sa.Boolean(),       nullable=False, server_default=sa.text("false")),
        sa.Column("insufficient_reason",   sa.Text(),          nullable=True),
        sa.Column("created_at",            sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.CheckConstraint(
            "forecast_type = 'Model-based forecast'",
            name="chk_forecast_type_label",
        ),
    )

    # ------------------------------------------------------------------
    # 5. benchmark_runs
    # ------------------------------------------------------------------
    op.create_table(
        "benchmark_runs",
        sa.Column("id",                       UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("run_at",                   sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("results",                  JSONB,          nullable=False, server_default=sa.text("'{}'") ),
        sa.Column("document_count_real",      sa.Integer(),   nullable=False, server_default="0"),
        sa.Column("document_count_synthetic", sa.Integer(),   nullable=False, server_default="0"),
        sa.Column("sample_size",              sa.Integer(),   nullable=False, server_default="0"),
        sa.Column("is_latest",                sa.Boolean(),   nullable=False, server_default="false"),
        sa.Column("run_note",                 sa.Text(),      nullable=True),
    )

    # ------------------------------------------------------------------
    # 6. benchmark_ground_truth
    # ------------------------------------------------------------------
    op.create_table(
        "benchmark_ground_truth",
        sa.Column("id",             UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("document_id",    UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="SET NULL"), nullable=True),
        sa.Column("label_set_name", sa.String(200),     nullable=False, unique=True),
        sa.Column("labels",         JSONB,              nullable=False, server_default=sa.text("'[]'")),
        sa.Column("is_synthetic",   sa.Boolean(),       nullable=False),
        sa.Column("synthetic_type", sa.String(50),      nullable=True),
        sa.Column("created_at",     sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.CheckConstraint(
            "(is_synthetic = false AND synthetic_type IS NULL) OR "
            "(is_synthetic = true AND synthetic_type IS NOT NULL)",
            name="chk_synthetic_type_consistency",
        ),
    )

    # ------------------------------------------------------------------
    # 7. Add is_synthetic + synthetic_type to documents
    # ------------------------------------------------------------------
    op.add_column("documents", sa.Column("is_synthetic",   sa.Boolean(), server_default="false", nullable=False))
    op.add_column("documents", sa.Column("synthetic_type", sa.Text(),    nullable=True))

    # ------------------------------------------------------------------
    # 8. Seed region_mapping from reference table
    # ------------------------------------------------------------------
    # Use op.execute with sa.text and explicit cast to avoid asyncpg JSON type issues.
    # Each row is inserted as a plain SQL statement with no JSONB params.
    for (entity_name, entity_type, region_id, region_name, state_name, source_note) in _REGION_SEED:
        # Escape single quotes in source_note
        safe_note = source_note.replace("'", "''")
        safe_name = entity_name.replace("'", "''")
        safe_rname = region_name.replace("'", "''")
        safe_sname = state_name.replace("'", "''")
        op.execute(sa.text(f"""
            INSERT INTO region_mapping (
                id, canonical_entity_id, region_id, region_name, state_name, source, source_note
            )
            SELECT
                gen_random_uuid(),
                ce.id,
                '{region_id}',
                '{safe_rname}',
                '{safe_sname}',
                'reference_table',
                '{safe_note}'
            FROM canonical_entities ce
            WHERE ce.canonical_name = '{safe_name}'
              AND ce.entity_type    = '{entity_type}'
            ON CONFLICT (canonical_entity_id) DO NOTHING
        """))

    # ------------------------------------------------------------------
    # 9. Seed benchmark_ground_truth from JSON files (non-fatal if missing)
    # ------------------------------------------------------------------
    import json
    from pathlib import Path

    gt_dir = Path(__file__).parent.parent.parent / "tests" / "benchmark_ground_truth"

    if gt_dir.exists():
        for json_file in gt_dir.rglob("*_labels.json"):
            try:
                data = json.loads(json_file.read_text())
                labels_json = json.dumps(data.get("labels", []))
                name = data.get("label_set_name", json_file.stem).replace("'", "''")
                synthetic = "true" if data.get("is_synthetic", False) else "false"
                stype_raw = data.get("synthetic_type")
                stype = f"'{stype_raw}'" if stype_raw else "NULL"
                op.execute(sa.text(f"""
                    INSERT INTO benchmark_ground_truth
                        (id, label_set_name, labels, is_synthetic, synthetic_type)
                    VALUES
                        (gen_random_uuid(), '{name}', '{labels_json}'::jsonb, {synthetic}, {stype})
                    ON CONFLICT (label_set_name) DO NOTHING
                """))
            except Exception as e:
                print(f"Warning: could not seed {json_file}: {e}")


def downgrade() -> None:
    op.drop_column("documents", "synthetic_type")
    op.drop_column("documents", "is_synthetic")
    op.drop_table("benchmark_ground_truth")
    op.drop_table("benchmark_runs")
    op.drop_table("forecast_results")
    op.drop_table("region_mapping")
    op.drop_table("parliamentary_queries")
    op.drop_table("users")
