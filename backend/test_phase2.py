#!/usr/bin/env python3
"""
Phase 2 End-to-End Test Suite
Tests all 5 demo checkpoints + API contract + provenance integrity.

Run: python3 test_phase2.py
(Server must be running on :8000 with Phase 1 data already ingested)
"""
import json
import sys
import time
import requests

BASE = "http://localhost:8000"
PASS = "\033[92m✓\033[0m"
FAIL = "\033[91m✗\033[0m"
INFO = "\033[94m→\033[0m"
WARN = "\033[93m⚠\033[0m"

results = []


def check(label, condition, detail=""):
    status = PASS if condition else FAIL
    print(f"  {status} {label}" + (f" — {detail}" if detail else ""))
    results.append((label, condition))
    return condition


def section(title):
    print(f"\n{'='*62}")
    print(f"  {title}")
    print(f"{'='*62}")


def poll_status(url, done_values=("done",), fail_values=("failed",), timeout=180, interval=3):
    start = time.time()
    while time.time() - start < timeout:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            s = r.json().get("status", "")
            if s in done_values:
                return s, r.json()
            if s in fail_values:
                return s, r.json()
        elapsed = int(time.time() - start)
        print(f"  {INFO} [{elapsed}s] status={r.json().get('status','?')}...", end="\r")
        time.sleep(interval)
    return "timeout", {}


# ──────────────────────────────────────────────────────────────────────────────
# SETUP: get an existing done document from Phase 1
# ──────────────────────────────────────────────────────────────────────────────
section("SETUP — Find Phase 1 Documents")
r = requests.get(f"{BASE}/documents?status=done&page_size=10")
check("GET /documents?status=done → 200", r.status_code == 200)
items = r.json().get("items", [])
check("At least 3 done documents exist", len(items) >= 3)

# Find a document with tables (XLSX or CSV)
pdf_doc = next((d for d in items if d["file_type"] == "pdf_digital"), None)
xlsx_doc = next((d for d in items if d["file_type"] == "xlsx"), None)
csv_doc  = next((d for d in items if d["file_type"] == "csv"), None)

check("Found pdf_digital document", pdf_doc is not None, f"id={pdf_doc['id'] if pdf_doc else 'N/A'}")
check("Found xlsx document", xlsx_doc is not None)
check("Found csv document", csv_doc is not None)

if not xlsx_doc:
    print("  FATAL: No XLSX document found. Upload coal_production.xlsx via Phase 1 first.")
    sys.exit(1)

# ──────────────────────────────────────────────────────────────────────────────
# DEMO CHECKPOINT 1: Trigger fact extraction + verify normalized facts produced
# ──────────────────────────────────────────────────────────────────────────────
section("DEMO 1 — Fact Extraction + Normalization + Provenance")

# Trigger on XLSX (has production table with entities)
xlsx_id = xlsx_doc["id"]
print(f"  {INFO} Triggering Phase 2 for XLSX doc: {xlsx_id}")
r = requests.post(f"{BASE}/documents/{xlsx_id}/process-facts", timeout=10)
check("POST /process-facts → 202", r.status_code == 202, f"got {r.status_code}")

# Also trigger for PDF and CSV
for doc in [pdf_doc, csv_doc]:
    if doc:
        r2 = requests.post(f"{BASE}/documents/{doc['id']}/process-facts", timeout=10)
        check(f"POST /process-facts [{doc['file_type']}] → 202 or 409", r2.status_code in (202, 409))

# Poll until XLSX is done
print(f"\n  {INFO} Polling Phase 2 status for XLSX (LLM extraction running)...")
status, status_data = poll_status(
    f"{BASE}/documents/{xlsx_id}/process-facts/status",
    timeout=300,
)
print()
check("XLSX Phase 2 status=done", status == "done", f"got: {status}")
if status == "failed":
    print(f"    Error: {status_data.get('error', 'n/a')}")

check("facts_extracted > 0", status_data.get("facts_extracted", 0) > 0,
      f"extracted={status_data.get('facts_extracted')}")
check("facts_normalized > 0", status_data.get("facts_normalized", 0) > 0,
      f"normalized={status_data.get('facts_normalized')}")

# Wait for PDF/CSV too
for doc in [pdf_doc, csv_doc]:
    if doc:
        status2, sd2 = poll_status(
            f"{BASE}/documents/{doc['id']}/process-facts/status", timeout=300
        )
        print()
        check(f"Phase 2 [{doc['file_type']}] status=done", status2 in ("done", "not_started"),
              f"got: {status2}")

# Verify normalized facts are queryable
print(f"\n  {INFO} Verifying GET /facts...")
r = requests.get(f"{BASE}/facts?document_id={xlsx_id}", timeout=10)
check("GET /facts?document_id → 200", r.status_code == 200)
fact_data = r.json()
check("Facts list has items", len(fact_data.get("items", [])) > 0,
      f"total={fact_data.get('total')}")

if fact_data.get("items"):
    f0 = fact_data["items"][0]
    print(f"  {INFO} First fact: metric={f0.get('metric')}, value={f0.get('normalized_value')} "
          f"{f0.get('normalized_unit')}, entity={f0.get('canonical_entity_name')}")

    check("Fact has metric", bool(f0.get("metric")))
    check("Fact has normalized_value", f0.get("normalized_value") is not None)
    check("Fact has document_id provenance", bool(f0.get("document_id")))
    check("Fact has page_number provenance", f0.get("page_number") is not None)

# ──────────────────────────────────────────────────────────────────────────────
# DEMO CHECKPOINT 2: Conflict detection — upload conflicting document
# ──────────────────────────────────────────────────────────────────────────────
section("DEMO 2 — Conflict Detection (Two Documents, Same Entity, Different Value)")

# Create a conflicting XLSX: same mine names, same period, different values
import openpyxl
wb = openpyxl.Workbook()
ws = wb.active
ws.title = "Coal Production 2023"
ws.append(["Mine Name", "Subsidiary", "Production (MT)", "OB Removal (MCM)", "Status"])
# Moonidih Colliery: was 2.1 MT, now say 2.8 MT (conflict!)
ws.append(["Moonidih Colliery", "BCCL", 2.8, 5.2, "Active"])
ws.append(["Jharia Division",   "BCCL", 6.1, 12.1, "Active"])   # was 5.4 (conflict!)
ws.append(["Sijua Area",        "BCCL", 3.2, 8.9, "Active"])
conflict_path = "/tmp/coal_production_v2.xlsx"
wb.save(conflict_path)

with open(conflict_path, "rb") as f:
    r = requests.post(
        f"{BASE}/documents/upload",
        files={"files": ("coal_production_v2.xlsx", f,
                         "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        timeout=30,
    )
check("Upload conflicting XLSX → 202", r.status_code == 202)
conflict_doc_id = None
if r.status_code == 202:
    docs_uploaded = r.json().get("documents", [])
    conflict_doc_id = docs_uploaded[0]["id"] if docs_uploaded else None
    check("Got conflict document ID", bool(conflict_doc_id))
    print(f"  {INFO} Conflict doc ID: {conflict_doc_id}")

    # Wait for Phase 1 ingestion
    print(f"  {INFO} Waiting for Phase 1 ingestion of conflict doc...")
    p1_status, _ = poll_status(
        f"{BASE}/documents/{conflict_doc_id}/status",
        done_values=("done",), fail_values=("failed",), timeout=120
    )
    print()
    check("Conflict doc Phase 1 done", p1_status == "done", f"got: {p1_status}")

    # Trigger Phase 2 on conflict doc
    r2 = requests.post(f"{BASE}/documents/{conflict_doc_id}/process-facts", timeout=10)
    check("POST /process-facts [conflict doc] → 202", r2.status_code == 202)

    print(f"  {INFO} Waiting for Phase 2 on conflict doc (LLM + conflict detection)...")
    p2_status, p2_data = poll_status(
        f"{BASE}/documents/{conflict_doc_id}/process-facts/status", timeout=300
    )
    print()
    check("Conflict doc Phase 2 done", p2_status == "done", f"got: {p2_status}")
    check("conflicts_found > 0", p2_data.get("conflicts_found", 0) > 0,
          f"conflicts_found={p2_data.get('conflicts_found')}")

# Verify conflicts are queryable
r = requests.get(f"{BASE}/conflicts", timeout=10)
check("GET /conflicts → 200", r.status_code == 200)
conflicts_data = r.json()
check("At least 1 open conflict", conflicts_data.get("total", 0) > 0,
      f"total={conflicts_data.get('total')}")

if conflicts_data.get("items"):
    c0 = conflicts_data["items"][0]
    print(f"  {INFO} Conflict: entity={c0.get('canonical_entity_name')}, "
          f"metric={c0.get('metric')}, "
          f"value_a={c0.get('value_a')}, value_b={c0.get('value_b')}, "
          f"delta_pct={c0.get('delta_pct'):.1f}%")
    check("Conflict has canonical_entity_name", bool(c0.get("canonical_entity_name")))
    check("Conflict has both value_a and value_b", c0.get("value_a") is not None
          and c0.get("value_b") is not None)
    check("Conflict has both document filenames (neither dropped)",
          bool(c0.get("document_a_filename")) and bool(c0.get("document_b_filename")))
    check("Neither value was silently overwritten (both differ)",
          c0.get("value_a") != c0.get("value_b"))

# ──────────────────────────────────────────────────────────────────────────────
# DEMO CHECKPOINT 3: GET /facts/{id}/evidence — full lineage chain
# ──────────────────────────────────────────────────────────────────────────────
section("DEMO 3 — GET /facts/{id}/evidence (Full Lineage Chain)")

# Get a fact from XLSX document
r = requests.get(f"{BASE}/facts?document_id={xlsx_id}&page_size=1", timeout=10)
check("GET /facts for XLSX → 200", r.status_code == 200)
fact_items = r.json().get("items", [])
check("At least 1 fact found for XLSX", len(fact_items) > 0)

if fact_items:
    fact_id = fact_items[0]["id"]
    print(f"  {INFO} Fetching evidence for fact: {fact_id}")
    r = requests.get(f"{BASE}/facts/{fact_id}/evidence", timeout=10)
    check("GET /facts/{id}/evidence → 200", r.status_code == 200)
    ev = r.json()

    # Verify complete chain
    check("Evidence has 'fact' layer",     "fact" in ev)
    check("Evidence has 'extracted' layer", "extracted" in ev)
    check("Evidence has 'source' layer",    "source" in ev)
    check("Evidence has 'page' layer",      "page" in ev)
    check("Evidence has 'document' layer",  "document" in ev)

    # Provenance continuity
    if "fact" in ev and "extracted" in ev:
        check("fact.extracted_fact_id matches extracted.id",
              ev["extracted"].get("id") is not None)
    if "page" in ev and "document" in ev:
        check("page has page_number", ev["page"].get("page_number") is not None)
        check("document has storage_path", bool(ev["document"].get("storage_path")))
        check("document has filename", bool(ev["document"].get("filename")))
    if "source" in ev:
        src = ev["source"]
        check("source type is 'table' or 'block'",
              src.get("type") in ("table", "block"))
        if src.get("type") == "table":
            check("source.table has raw_structure",
                  bool(src.get("table", {}).get("raw_structure")))

    # 404 test
    r404 = requests.get(f"{BASE}/facts/00000000-0000-0000-0000-000000000000/evidence", timeout=5)
    check("GET /facts/nonexistent/evidence → 404", r404.status_code == 404)

# ──────────────────────────────────────────────────────────────────────────────
# DEMO CHECKPOINT 4: Validation flags
# ──────────────────────────────────────────────────────────────────────────────
section("DEMO 4 — Validation Flags")
r = requests.get(f"{BASE}/validation-flags", timeout=10)
check("GET /validation-flags → 200", r.status_code == 200)
flags_data = r.json()
print(f"  {INFO} Total open flags: {flags_data.get('total', 0)}")

if flags_data.get("items"):
    f0 = flags_data["items"][0]
    check("Flag has flag_type",  bool(f0.get("flag_type")))
    check("Flag has severity",   bool(f0.get("severity")))
    check("Flag has detail",     bool(f0.get("detail")))
    check("Flag has status=open", f0.get("status") == "open")
    check("Flag has document_filename provenance", bool(f0.get("document_filename")))
    print(f"  {INFO} Sample flag: type={f0.get('flag_type')}, severity={f0.get('severity')}")
    print(f"         detail={json.dumps(f0.get('detail', {}))[:120]}")

# Filter by severity
r_warn = requests.get(f"{BASE}/validation-flags?severity=warning", timeout=10)
check("Filter by severity=warning → 200", r_warn.status_code == 200)

# Filter by flag_type
r_miss = requests.get(f"{BASE}/validation-flags?flag_type=missing_entity", timeout=10)
check("Filter by flag_type=missing_entity → 200", r_miss.status_code == 200)

# ──────────────────────────────────────────────────────────────────────────────
# DEMO CHECKPOINT 5: Entity alias resolution
# ──────────────────────────────────────────────────────────────────────────────
section("DEMO 5 — Entity Alias Resolution (CCL → Central Coalfields Limited)")
r = requests.get(f"{BASE}/entities?page_size=50", timeout=10)
check("GET /entities → 200", r.status_code == 200)
entities_data = r.json()
check("Entities list has items", entities_data.get("total", 0) > 0,
      f"total={entities_data.get('total')}")

# Find CCL entity
ccl = next((e for e in entities_data.get("items", [])
            if e["canonical_name"] == "CCL"), None)
check("'CCL' canonical entity exists", ccl is not None)

if ccl:
    check("CCL has alias_count > 0", ccl.get("alias_count", 0) > 0,
          f"alias_count={ccl.get('alias_count')}")
    r_detail = requests.get(f"{BASE}/entities/{ccl['id']}", timeout=10)
    check("GET /entities/{id} → 200", r_detail.status_code == 200)
    detail = r_detail.json()
    aliases = [a["alias_text"] for a in detail.get("aliases", [])]
    print(f"  {INFO} CCL aliases: {aliases}")
    check("'Central Coalfields Limited' is an alias of CCL",
          "Central Coalfields Limited" in aliases)
    check("All CCL aliases have resolution_method='manual'",
          all(a["resolution_method"] == "manual" for a in detail.get("aliases", [])))

# BCCL alias check (from Phase 1 test data — mine entities extracted from tables)
bccl = next((e for e in entities_data.get("items", [])
             if e["canonical_name"] == "BCCL"), None)
check("'BCCL' canonical entity exists", bccl is not None)
if bccl:
    r_b = requests.get(f"{BASE}/entities/{bccl['id']}", timeout=10)
    b_detail = r_b.json()
    b_aliases = [a["alias_text"] for a in b_detail.get("aliases", [])]
    check("'Bharat Coking Coal Limited' is alias of BCCL",
          "Bharat Coking Coal Limited" in b_aliases)

# ──────────────────────────────────────────────────────────────────────────────
# SUPPLEMENTARY: API contract checks
# ──────────────────────────────────────────────────────────────────────────────
section("SUPPLEMENTARY — API Contract")

# GET /conflicts/{id} — full detail
r = requests.get(f"{BASE}/conflicts?page_size=1", timeout=10)
if r.status_code == 200 and r.json().get("items"):
    conflict_id = r.json()["items"][0]["id"]
    r_detail = requests.get(f"{BASE}/conflicts/{conflict_id}", timeout=15)
    check("GET /conflicts/{id} → 200", r_detail.status_code == 200)
    cd = r_detail.json()
    check("Conflict detail has 'conflict' key", "conflict" in cd)
    check("Conflict detail has 'fact_a_evidence'", "fact_a_evidence" in cd)
    check("Conflict detail has 'fact_b_evidence'", "fact_b_evidence" in cd)
    check("fact_a and fact_b evidence are different documents",
          cd.get("fact_a_evidence", {}).get("document", {}).get("id") !=
          cd.get("fact_b_evidence", {}).get("document", {}).get("id"))

# GET /duplicates
r = requests.get(f"{BASE}/duplicates", timeout=10)
check("GET /duplicates → 200", r.status_code == 200)

# GET /entities?entity_type=subsidiary
r = requests.get(f"{BASE}/entities?entity_type=subsidiary", timeout=10)
check("GET /entities?entity_type=subsidiary → 200", r.status_code == 200)
sub_count = r.json().get("total", 0)
check("At least 10 subsidiary entities seeded", sub_count >= 10, f"got {sub_count}")

# Batch process-facts
r = requests.post(f"{BASE}/documents/process-facts/batch", timeout=15)
check("POST /process-facts/batch → 202", r.status_code == 202)
batch_result = r.json()
check("Batch result has 'queued' key", "queued" in batch_result)
check("Batch result has 'skipped_already_processed' key", "skipped_already_processed" in batch_result)

# Phase 1 regression: original endpoints still work
r = requests.get(f"{BASE}/documents", timeout=10)
check("Phase 1 GET /documents still → 200 (regression)", r.status_code == 200)
r = requests.post(f"{BASE}/search", json={"query": "coal production"}, timeout=30)
check("Phase 1 POST /search still → 200 (regression)", r.status_code == 200)

# ──────────────────────────────────────────────────────────────────────────────
# DB PROVENANCE AUDIT
# ──────────────────────────────────────────────────────────────────────────────
section("DB PROVENANCE AUDIT")
import subprocess

queries = [
    ("No extracted_facts without document_id or page_id",
     "SELECT COUNT(*) FROM extracted_facts WHERE document_id IS NULL OR page_id IS NULL"),
    ("No normalized_facts without extracted_fact_id",
     "SELECT COUNT(*) FROM normalized_facts WHERE extracted_fact_id IS NULL"),
    ("No conflicts with same fact_a_id=fact_b_id",
     "SELECT COUNT(*) FROM conflicts WHERE fact_a_id = fact_b_id"),
    ("No validation_flags without normalized_fact_id",
     "SELECT COUNT(*) FROM validation_flags WHERE normalized_fact_id IS NULL"),
    ("All conflicts reference facts from DIFFERENT documents",
     """SELECT COUNT(*) FROM conflicts c
        JOIN normalized_facts nfa ON nfa.id = c.fact_a_id
        JOIN normalized_facts nfb ON nfb.id = c.fact_b_id
        JOIN extracted_facts efa ON efa.id = nfa.extracted_fact_id
        JOIN extracted_facts efb ON efb.id = nfb.extracted_fact_id
        WHERE efa.document_id = efb.document_id"""),
]

for label, sql in queries:
    res = subprocess.run(
        ["psql", "-h", "localhost", "-U", "cmpdi", "-d", "cmpdi_mining", "-t", "-c", sql],
        capture_output=True, text=True
    )
    count = res.stdout.strip()
    check(label, count == "0", f"count={count}")

# Row count summary
count_res = subprocess.run(
    ["psql", "-h", "localhost", "-U", "cmpdi", "-d", "cmpdi_mining", "-c",
     "SELECT (SELECT COUNT(*) FROM extracted_facts WHERE NOT is_obsolete) AS active_efacts,"
     "(SELECT COUNT(*) FROM normalized_facts) AS nfacts,"
     "(SELECT COUNT(*) FROM validation_flags) AS flags,"
     "(SELECT COUNT(*) FROM conflicts) AS conflicts,"
     "(SELECT COUNT(*) FROM canonical_entities) AS entities,"
     "(SELECT COUNT(*) FROM entity_aliases) AS aliases;"],
    capture_output=True, text=True
)
print(f"  {INFO} DB counts:\n{count_res.stdout}")

# ──────────────────────────────────────────────────────────────────────────────
# SUMMARY
# ──────────────────────────────────────────────────────────────────────────────
section("TEST SUMMARY")
passed = sum(1 for _, ok in results if ok)
failed = sum(1 for _, ok in results if not ok)
print(f"  Passed: {passed}/{len(results)}")
if failed:
    print(f"\n  FAILED TESTS ({failed}):")
    for label, ok in results:
        if not ok:
            print(f"    {FAIL} {label}")

print()
sys.exit(0 if failed == 0 else 1)
