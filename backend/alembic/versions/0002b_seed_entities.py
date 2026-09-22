"""Seed canonical entities — CIL subsidiaries, major mines, coalfields.

Revision ID: 0002b
Revises:     0002
Create Date: 2026-09-20
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from alembic import op

revision: str = "0002b"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# fmt: off
# (canonical_name, entity_type, description)
ENTITIES = [
    # CIL Subsidiaries
    ("Coal India Limited",              "subsidiary",  "Parent holding company"),
    ("BCCL",                            "subsidiary",  "Bharat Coking Coal Limited"),
    ("CCL",                             "subsidiary",  "Central Coalfields Limited"),
    ("ECL",                             "subsidiary",  "Eastern Coalfields Limited"),
    ("WCL",                             "subsidiary",  "Western Coalfields Limited"),
    ("MCL",                             "subsidiary",  "Mahanadi Coalfields Limited"),
    ("NCL",                             "subsidiary",  "Northern Coalfields Limited"),
    ("SECL",                            "subsidiary",  "South Eastern Coalfields Limited"),
    ("NEC",                             "subsidiary",  "North Eastern Coalfields"),
    ("CMPDI",                           "subsidiary",  "Central Mine Planning & Design Institute"),
    # Major Mines (from Phase 1 test data)
    ("Moonidih Colliery",               "mine",        "Underground coking coal mine, BCCL"),
    ("Jharia Division",                 "mine",        "BCCL operational division, Jharia coalfield"),
    ("Sijua Area",                      "mine",        "BCCL Sijua area collieries"),
    ("Katras Area",                     "mine",        "BCCL Katras area collieries"),
    ("Patherdih Colliery",              "mine",        "BCCL colliery"),
    # Coalfields
    ("Jharia Coalfield",                "coalfield",   "Premier coking coal reserve, Jharkhand"),
    ("Raniganj Coalfield",              "coalfield",   "Oldest coalfield in India, West Bengal"),
    ("Bokaro Coalfield",                "coalfield",   "Jharkhand coalfield"),
    ("North Karanpura Coalfield",       "coalfield",   "Jharkhand coalfield"),
    ("Singrauli Coalfield",             "coalfield",   "Madhya Pradesh / Uttar Pradesh"),
    # Survey locations (from Phase 1 CSV test data)
    ("Jharia Block A",                  "location",    "Jharia coalfield survey block A"),
    ("Jharia Block B",                  "location",    "Jharia coalfield survey block B"),
    ("Bokaro Site 1",                   "location",    "Bokaro coalfield survey site 1"),
    ("Raniganj East",                   "location",    "Raniganj coalfield eastern section"),
]

# (alias_text, canonical_name, entity_type, resolution_method, confidence)
ALIASES = [
    # CIL / Coal India aliases
    ("CIL",                                     "Coal India Limited",    "subsidiary", "manual", 1.0),
    ("Coal India",                              "Coal India Limited",    "subsidiary", "manual", 1.0),
    # BCCL aliases
    ("Bharat Coking Coal Limited",              "BCCL",  "subsidiary", "manual", 1.0),
    ("Bharat Coking Coal Ltd",                  "BCCL",  "subsidiary", "manual", 1.0),
    ("Bharat Coking Coal Ltd.",                 "BCCL",  "subsidiary", "manual", 1.0),
    # CCL aliases
    ("Central Coalfields Limited",              "CCL",   "subsidiary", "manual", 1.0),
    ("Central Coalfields Ltd",                  "CCL",   "subsidiary", "manual", 1.0),
    ("Central Coalfields Ltd.",                 "CCL",   "subsidiary", "manual", 1.0),
    # ECL
    ("Eastern Coalfields Limited",              "ECL",   "subsidiary", "manual", 1.0),
    ("Eastern Coalfields Ltd",                  "ECL",   "subsidiary", "manual", 1.0),
    # WCL
    ("Western Coalfields Limited",              "WCL",   "subsidiary", "manual", 1.0),
    ("Western Coalfields Ltd",                  "WCL",   "subsidiary", "manual", 1.0),
    # MCL
    ("Mahanadi Coalfields Limited",             "MCL",   "subsidiary", "manual", 1.0),
    ("Mahanadi Coalfields Ltd",                 "MCL",   "subsidiary", "manual", 1.0),
    # NCL
    ("Northern Coalfields Limited",             "NCL",   "subsidiary", "manual", 1.0),
    ("Northern Coalfields Ltd",                 "NCL",   "subsidiary", "manual", 1.0),
    # SECL
    ("South Eastern Coalfields Limited",        "SECL",  "subsidiary", "manual", 1.0),
    ("South Eastern Coalfields Ltd",            "SECL",  "subsidiary", "manual", 1.0),
    # CMPDI
    ("Central Mine Planning & Design Institute","CMPDI", "subsidiary", "manual", 1.0),
    ("CMPDI Ltd",                               "CMPDI", "subsidiary", "manual", 1.0),
    # Coalfield aliases
    ("Jharia",                                  "Jharia Coalfield",   "coalfield", "manual", 0.9),
    ("Raniganj",                                "Raniganj Coalfield", "coalfield", "manual", 0.9),
    ("Bokaro",                                  "Bokaro Coalfield",   "coalfield", "manual", 0.9),
    # Location aliases (from Phase 1 CSV)
    ("Jharia_Block_A",                          "Jharia Block A",  "location", "manual", 1.0),
    ("Jharia_Block_B",                          "Jharia Block B",  "location", "manual", 1.0),
    ("Bokaro_Site_1",                           "Bokaro Site 1",   "location", "manual", 1.0),
    ("Raniganj_East",                           "Raniganj East",   "location", "manual", 1.0),
]
# fmt: on


def upgrade() -> None:
    conn = op.get_bind()

    # Insert entities, get back their IDs
    entity_id_map: dict[tuple[str, str], str] = {}
    for name, etype, desc in ENTITIES:
        result = conn.execute(
            sa.text("""
                INSERT INTO canonical_entities (canonical_name, entity_type, description)
                VALUES (:name, :etype, :desc)
                ON CONFLICT (canonical_name, entity_type) DO UPDATE
                    SET description = EXCLUDED.description
                RETURNING id
            """),
            {"name": name, "etype": etype, "desc": desc},
        )
        row = result.fetchone()
        entity_id_map[(name, etype)] = str(row[0])

    # Insert aliases — pass entity UUID as plain string; asyncpg handles the cast
    for alias_text, canonical_name, entity_type, method, conf in ALIASES:
        entity_id = entity_id_map.get((canonical_name, entity_type))
        if entity_id is None:
            continue
        conn.execute(
            sa.text("""
                INSERT INTO entity_aliases (canonical_entity_id, alias_text, resolution_method, confidence)
                VALUES (CAST(:eid AS uuid), :alias, :method, :conf)
                ON CONFLICT (alias_text) DO NOTHING
            """),
            {"eid": entity_id, "alias": alias_text, "method": method, "conf": conf},
        )



def downgrade() -> None:
    # Aliases are cascade-deleted with entities
    op.execute("DELETE FROM canonical_entities")
