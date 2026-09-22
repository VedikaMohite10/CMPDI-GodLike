#!/usr/bin/env python3
"""
Phase 1 End-to-End Test Suite
Tests all 7 demo checkpoints and retrieval contract requirements.
Run: python3 test_phase1.py
"""
import json
import sys
import time
import uuid
import requests

BASE = "http://localhost:8000"
PASS = "\033[92m✓\033[0m"
FAIL = "\033[91m✗\033[0m"
INFO = "\033[94m→\033[0m"

results = []

def check(label, condition, detail=""):
    status = PASS if condition else FAIL
    print(f"  {status} {label}" + (f" — {detail}" if detail else ""))
    results.append((label, condition))
    return condition

def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

# ──────────────────────────────────────────────────────────────
# 1. HEALTH CHECK
# ──────────────────────────────────────────────────────────────
section("CHECK 1 — Health Endpoint")
r = requests.get(f"{BASE}/health", timeout=5)
check("GET /health returns 200", r.status_code == 200)
data = r.json()
check("Response has 'status: ok'", data.get("status") == "ok", f"got: {data}")
check("Response has version field", "version" in data, f"version={data.get('version')}")

# ──────────────────────────────────────────────────────────────
# 2. DOCUMENT UPLOAD — 4 different file types
# ──────────────────────────────────────────────────────────────
section("CHECK 2 — Upload 4 Test Documents")

doc_ids = {}
TEST_FILES = {
    "digital_pdf": ("/tmp/cmpdi_test_docs/digital_report.pdf", "application/pdf"),
    "xlsx":        ("/tmp/cmpdi_test_docs/coal_production.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
    "csv":         ("/tmp/cmpdi_test_docs/survey_data.csv", "text/csv"),
    "image":       ("/tmp/cmpdi_test_docs/site_map.png", "image/png"),
}

for label, (path, mime) in TEST_FILES.items():
    with open(path, "rb") as f:
        r = requests.post(
            f"{BASE}/documents/upload",
            files={"files": (path.split("/")[-1], f, mime)},
            timeout=30,
        )
    ok = r.status_code == 202
    check(f"POST /upload {label} → 202", ok, f"got {r.status_code}")
    if ok:
        docs = r.json().get("documents", [])
        check(f"  {label} returns document ID", len(docs) > 0)
        if docs:
            doc_id = docs[0]["id"]
            doc_ids[label] = doc_id
            status = docs[0]["processing_status"]
            check(f"  {label} initial status='pending'", status == "pending", f"got: {status}")
            print(f"  {INFO} Document ID: {doc_id}")

# ──────────────────────────────────────────────────────────────
# 3. POLL UNTIL DONE
# ──────────────────────────────────────────────────────────────
section("CHECK 3 — Poll Processing Status Until Done")

timeout_secs = 180
poll_interval = 3
print(f"  {INFO} Waiting up to {timeout_secs}s for all documents to finish processing...")
print(f"  {INFO} (Embedding via bge-m3 Ollama call — may take ~30s per document)")

start = time.time()
final_statuses = {}

while time.time() - start < timeout_secs:
    all_done = True
    for label, doc_id in doc_ids.items():
        if final_statuses.get(label) in ("done", "failed"):
            continue
        r = requests.get(f"{BASE}/documents/{doc_id}/status", timeout=10)
        if r.status_code == 200:
            s = r.json().get("processing_status", "unknown")
            final_statuses[label] = s
            if s not in ("done", "failed"):
                all_done = False
    if all_done:
        break
    elapsed = int(time.time() - start)
    pending = [l for l, s in final_statuses.items() if s not in ("done","failed")]
    print(f"  {INFO} [{elapsed}s] Still processing: {pending}", end="\r")
    time.sleep(poll_interval)

print()
for label, doc_id in doc_ids.items():
    s = final_statuses.get(label, "unknown")
    check(f"Document '{label}' status=done", s == "done", f"got: {s}")
    if s == "failed":
        r2 = requests.get(f"{BASE}/documents/{doc_id}/status")
        print(f"    Error: {r2.json().get('processing_error', 'n/a')}")

# ──────────────────────────────────────────────────────────────
# 4. LIST DOCUMENTS
# ──────────────────────────────────────────────────────────────
section("CHECK 4 — GET /documents (List with Pagination)")
r = requests.get(f"{BASE}/documents?page=1&page_size=20", timeout=10)
check("GET /documents returns 200", r.status_code == 200)
data = r.json()
check("Response has 'items' list", "items" in data)
check("Response has 'total' count", "total" in data, f"total={data.get('total')}")
check("Response has 'page' field", "page" in data)
check(f"At least {len(doc_ids)} documents listed", data.get("total", 0) >= len(doc_ids))

# Filter by status=done
r2 = requests.get(f"{BASE}/documents?status=done", timeout=10)
check("Filter by status=done works", r2.status_code == 200)
done_items = r2.json().get("items", [])
check("Filtered list only has done documents", all(d["processing_status"] == "done" for d in done_items))

# ──────────────────────────────────────────────────────────────
# 5. DOCUMENT DETAIL with EXTRACTION SUMMARY
# ──────────────────────────────────────────────────────────────
section("CHECK 5 — GET /documents/{id} (Detail + Extraction Summary)")
if "digital_pdf" in doc_ids:
    doc_id = doc_ids["digital_pdf"]
    r = requests.get(f"{BASE}/documents/{doc_id}", timeout=10)
    check("GET /documents/{id} returns 200", r.status_code == 200)
    d = r.json()
    check("Has 'id' field", "id" in d)
    check("Has 'file_type' field", "file_type" in d, f"type={d.get('file_type')}")
    check("Has 'storage_path' (via extraction_summary)", "extraction_summary" in d)
    summary = d.get("extraction_summary", {})
    check("Extraction summary has text_blocks count", "total_text_blocks" in summary, f"blocks={summary.get('total_text_blocks')}")
    check("Extraction summary has tables count", "total_tables" in summary)
    check("Extraction summary has vectors_indexed count", "total_vectors_indexed" in summary, f"vectors={summary.get('total_vectors_indexed')}")
    print(f"  {INFO} Extraction summary: {json.dumps(summary, indent=4)}")

    # 404 test
    r404 = requests.get(f"{BASE}/documents/{uuid.uuid4()}", timeout=5)
    check("GET /documents/nonexistent → 404", r404.status_code == 404)

# ──────────────────────────────────────────────────────────────
# 6. PAGE CONTENT with PROVENANCE
# ──────────────────────────────────────────────────────────────
section("CHECK 6 — GET /documents/{id}/pages/1 (Provenance Verification)")

for label in ["digital_pdf", "xlsx", "csv"]:
    if label not in doc_ids:
        continue
    doc_id = doc_ids[label]
    r = requests.get(f"{BASE}/documents/{doc_id}/pages/1", timeout=10)
    check(f"GET /pages/1 [{label}] returns 200", r.status_code == 200, f"got {r.status_code}")
    if r.status_code != 200:
        print(f"    Error: {r.text[:200]}")
        continue
    page = r.json()
    check(f"  [{label}] page has 'document_id'", "document_id" in page)
    check(f"  [{label}] page has 'page_id'", "page_id" in page)
    check(f"  [{label}] page_id matches document_id ref", page.get("document_id") == str(doc_id))

    # Provenance on text blocks
    blocks = page.get("text_blocks", [])
    tables = page.get("tables", [])
    if blocks:
        b = blocks[0]
        check(f"  [{label}] text_block has document_id", b.get("document_id") == str(doc_id))
        check(f"  [{label}] text_block has page_id", "page_id" in b)
        check(f"  [{label}] text_block has text", bool(b.get("text")))
        print(f"  {INFO} First block excerpt: {b.get('text','')[:80]!r}")
    if tables:
        t = tables[0]
        check(f"  [{label}] table has document_id", t.get("document_id") == str(doc_id))
        check(f"  [{label}] table has raw_structure", "raw_structure" in t)
        rs = t.get("raw_structure", {})
        check(f"  [{label}] table raw_structure has headers+rows", "headers" in rs and "rows" in rs)
        print(f"  {INFO} Table shape: {rs.get('shape')}, headers: {rs.get('headers')}")

# ──────────────────────────────────────────────────────────────
# 7. ORIGINAL FILE DOWNLOAD (retrieval contract #4)
# ──────────────────────────────────────────────────────────────
section("CHECK 7 — GET /documents/{id}/original (Retrieval Contract #4 & #5)")
for label, doc_id in doc_ids.items():
    r = requests.get(f"{BASE}/documents/{doc_id}/original", timeout=30)
    ok = r.status_code == 200
    check(f"GET /original [{label}] → 200", ok, f"got {r.status_code}")
    if ok:
        check(f"  [{label}] response has Content-Disposition", "content-disposition" in r.headers)
        check(f"  [{label}] file has non-zero bytes", len(r.content) > 0, f"size={len(r.content)}")

# ──────────────────────────────────────────────────────────────
# 8. SEMANTIC SEARCH (with full provenance)
# ──────────────────────────────────────────────────────────────
section("CHECK 8 — POST /search (Retrieval Contract #6 & #7)")
r = requests.post(
    f"{BASE}/search",
    json={"query": "coal production Jharia mines 2023", "top_k": 5},
    timeout=60,
)
check("POST /search returns 200", r.status_code == 200, f"got {r.status_code}")
if r.status_code == 200:
    data = r.json()
    check("Response has 'query' echo", data.get("query") == "coal production Jharia mines 2023")
    results_list = data.get("results", [])
    check("At least 1 result returned", len(results_list) > 0, f"got {len(results_list)}")
    if results_list:
        hit = results_list[0]
        print(f"  {INFO} Top result score: {hit.get('score', 0):.4f}")
        print(f"  {INFO} Excerpt: {hit.get('text_excerpt','')[:80]!r}")
        # Provenance chain check (retrieval contract point #6)
        check("  result has 'document_id'", "document_id" in hit)
        check("  result has 'page_id'", "page_id" in hit)
        check("  result has 'block_id'", "block_id" in hit)
        check("  result has 'qdrant_point_id'", "qdrant_point_id" in hit)
        check("  result has 'page_number'", "page_number" in hit)
        check("  result has 'block_type'", "block_type" in hit)
        check("  result has 'document_filename'", "document_filename" in hit)
        # Verify we can follow Qdrant→Postgres→original chain
        doc_id_from_search = hit["document_id"]
        page_num = hit["page_number"]
        r2 = requests.get(f"{BASE}/documents/{doc_id_from_search}/pages/{page_num}", timeout=10)
        check("  Qdrant→Postgres chain: can fetch page by search doc_id+page_num", r2.status_code == 200)
        r3 = requests.get(f"{BASE}/documents/{doc_id_from_search}/original", timeout=10)
        check("  Postgres→File chain: can fetch original by search doc_id alone", r3.status_code == 200)

# Filter by file_type
r_filtered = requests.post(
    f"{BASE}/search",
    json={"query": "coal production", "top_k": 5, "filter": {"file_type": "pdf_digital"}},
    timeout=60,
)
check("POST /search with file_type filter → 200", r_filtered.status_code == 200)

# Empty query → 422 (Pydantic min_length=1 validation fires before router)
r_bad = requests.post(f"{BASE}/search", json={"query": ""}, timeout=5)
check("POST /search with empty query → 422 (Pydantic validation)", r_bad.status_code == 422)

# ──────────────────────────────────────────────────────────────
# 9. PROVENANCE DB VALIDATION
# ──────────────────────────────────────────────────────────────
section("CHECK 9 — Provenance DB Audit (No Orphan Records)")
import subprocess
queries = [
    ("No text_blocks without document_id or page_id",
     "SELECT COUNT(*) FROM extracted_text_blocks WHERE document_id IS NULL OR page_id IS NULL"),
    ("No tables without document_id or page_id",
     "SELECT COUNT(*) FROM extracted_tables WHERE document_id IS NULL OR page_id IS NULL"),
    ("No images without document_id or page_id",
     "SELECT COUNT(*) FROM extracted_images WHERE document_id IS NULL OR page_id IS NULL"),
    ("No vector_index_log without block_id or qdrant_point_id",
     "SELECT COUNT(*) FROM vector_index_log WHERE block_id IS NULL OR qdrant_point_id IS NULL"),
    ("No documents without storage_path",
     "SELECT COUNT(*) FROM documents WHERE storage_path IS NULL OR storage_path = ''"),
]
for label, sql in queries:
    res = subprocess.run(
        ["psql", "-h", "localhost", "-U", "cmpdi", "-d", "cmpdi_mining", "-t", "-c", sql],
        capture_output=True, text=True
    )
    count = res.stdout.strip()
    check(label, count == "0", f"orphan count={count}")

# Row counts
count_res = subprocess.run(
    ["psql", "-h", "localhost", "-U", "cmpdi", "-d", "cmpdi_mining", "-c",
     "SELECT (SELECT COUNT(*) FROM documents) AS docs, (SELECT COUNT(*) FROM pages) AS pages, "
     "(SELECT COUNT(*) FROM extracted_text_blocks) AS blocks, (SELECT COUNT(*) FROM extracted_tables) AS tables, "
     "(SELECT COUNT(*) FROM extracted_images) AS images, (SELECT COUNT(*) FROM vector_index_log) AS vectors;"],
    capture_output=True, text=True
)
print(f"  {INFO} DB row counts:\n{count_res.stdout}")

# ──────────────────────────────────────────────────────────────
# SUMMARY
# ──────────────────────────────────────────────────────────────
section("TEST SUMMARY")
passed = sum(1 for _, ok in results if ok)
failed = sum(1 for _, ok in results if not ok)
total = len(results)
print(f"  Passed: {passed}/{total}")
if failed:
    print(f"\n  FAILED TESTS:")
    for label, ok in results:
        if not ok:
            print(f"    {FAIL} {label}")

print()
sys.exit(0 if failed == 0 else 1)
