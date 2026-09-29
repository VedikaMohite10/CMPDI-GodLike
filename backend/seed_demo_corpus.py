#!/usr/bin/env python3
"""
Demo corpus generator + uploader — fixed version.
Correct response field: 'documents' (not 'uploaded')
Correct status endpoint: /documents/{id}/process-facts/status
"""
import io, os, time, json, requests
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

BASE = "http://localhost:8000"

def get_token(username, password):
    r = requests.post(f"{BASE}/auth/login",
                      data={"username": username, "password": password})
    r.raise_for_status()
    return r.json()["access_token"]

TOKEN = get_token("admin", "changeme123!")
HEADERS = {"Authorization": f"Bearer {TOKEN}"}

def api(method, path, **kw):
    r = getattr(requests, method)(f"{BASE}{path}", headers=HEADERS, **kw)
    if not r.ok:
        print(f"  ⚠ {method.upper()} {path} → {r.status_code}: {r.text[:300]}")
    return r

# ── Styling helpers ────────────────────────────────────────────────────────────
HEADER_FILL = PatternFill("solid", fgColor="1F4E79")
HEADER_FONT = Font(bold=True, color="FFFFFF")
ALT_FILL    = PatternFill("solid", fgColor="D6E4F0")

def _hdr(ws, row, cols):
    for c, val in enumerate(cols, 1):
        cell = ws.cell(row=row, column=c, value=val)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal="center")

def _row(ws, row_num, values, alt=False):
    fill = ALT_FILL if alt else None
    for c, val in enumerate(values, 1):
        cell = ws.cell(row=row_num, column=c, value=val)
        if fill:
            cell.fill = fill

def _autofit(ws):
    for col in ws.columns:
        max_len = max((len(str(c.value or "")) for c in col), default=8)
        ws.column_dimensions[get_column_letter(col[0].column)].width = min(max_len + 4, 45)

def _xlsx_buf(wb):
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf

# ── Document builders ──────────────────────────────────────────────────────────

CIL_YEARS = [
    ("FY 2018-19", 606.89, 598.61, 1358.32, 297144),
    ("FY 2019-20", 602.14, 605.43, 1312.78, 283114),
    ("FY 2020-21", 596.22, 578.22, 1190.56, 272453),
    ("FY 2021-22", 623.13, 616.11, 1265.45, 259681),
    ("FY 2022-23", 703.21, 694.03, 1421.89, 248765),
    ("FY 2023-24", 773.65, 764.88, 1518.22, 241398),
]

def make_cil_annual(fy, prod, disp, ob, manpower):
    wb = openpyxl.Workbook()
    ws1 = wb.active
    ws1.title = "Performance Summary"
    ws1['A1'] = f"Coal India Limited — Annual Performance Report — {fy}"
    ws1['A1'].font = Font(bold=True, size=14)
    ws1['A2'] = "Source: CIL Annual Report | Ministry of Coal, Government of India"
    ws1['A3'] = ""
    _hdr(ws1, 4, ["Metric", "Value", "Unit", "Period", "Notes"])
    data = [
        ("Coal Production",    prod,     "MT",  fy, "Raw coal production including washery rejects"),
        ("Coal Dispatch",      disp,     "MT",  fy, "Total coal dispatched to consumers"),
        ("Overburden Removal", ob,       "MCM", fy, "OB removal in all open cast mines"),
        ("Manpower",           manpower, "Nos", fy, "Total regular employees as on 31 March"),
    ]
    for i, r in enumerate(data, 5):
        _row(ws1, i, r, alt=(i%2==0))

    # Also add prose text block for heuristic extraction
    ws2 = wb.create_sheet("Key Highlights")
    ws2['A1'] = f"Key Highlights — Coal India Limited — {fy}"
    ws2['A1'].font = Font(bold=True, size=13)
    ws2['A3'] = f"Coal India Limited achieved total coal production of {prod} MT during {fy}."
    ws2['A4'] = f"Coal dispatch was {disp} MT against the annual target."
    ws2['A5'] = f"Overburden removal stood at {ob} MCM during the year."
    ws2['A6'] = f"Total manpower of CIL was {manpower} employees."
    _autofit(ws1)
    return _xlsx_buf(wb)

def make_mcl_report():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "MCL Production Data"
    ws['A1'] = "Mahanadi Coalfields Limited (MCL) — Annual Production Statistics"
    ws['A1'].font = Font(bold=True, size=13)
    ws['A2'] = "Source: MCL Annual Reports 2018-2024 | CIL Subsidiary"
    ws['A3'] = ""
    _hdr(ws, 4, ["Fiscal Year", "Coal Production (MT)", "Coal Dispatch (MT)", "OB Removal (MCM)", "Manpower"])
    rows = [
        ("FY 2018-19", 138.22, 136.88, 312.45, 19455),
        ("FY 2019-20", 141.55, 139.33, 328.67, 18934),
        ("FY 2020-21", 148.77, 145.22, 345.12, 18344),
        ("FY 2021-22", 155.44, 153.11, 367.89, 17823),
        ("FY 2022-23", 170.23, 168.55, 398.34, 17312),
        ("FY 2023-24", 189.44, 187.22, 432.11, 16988),
    ]
    for i, r in enumerate(rows, 5):
        _row(ws, i, r, alt=(i%2==0))
    ws2 = wb.create_sheet("Highlights")
    ws2['A1'] = "MCL Key Performance Highlights"
    ws2['A1'].font = Font(bold=True)
    ws2['A3'] = "MCL recorded coal production of 189.44 MT during FY 2023-24, highest ever."
    ws2['A4'] = "Coal dispatch by MCL was 187.22 MT in FY 2023-24."
    ws2['A5'] = "Overburden removal was 432.11 MCM, up from 398.34 MCM in FY 2022-23."
    _autofit(ws)
    return _xlsx_buf(wb)

def make_bccl_report():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "BCCL Production Data"
    ws['A1'] = "BCCL (Bharat Coking Coal Limited) — Multi-Year Production Statistics"
    ws['A1'].font = Font(bold=True, size=13)
    ws['A2'] = "Source: BCCL Annual Reports | Jharia Coalfield, Jharkhand"
    ws['A3'] = ""
    _hdr(ws, 4, ["Fiscal Year", "Coal Production (MT)", "Coal Dispatch (MT)", "OB Removal (MCM)"])
    rows = [
        ("FY 2018-19", 32.47, 31.89, 154.32),
        ("FY 2019-20", 31.55, 30.99, 148.91),
        ("FY 2020-21", 29.88, 28.44, 132.67),
        ("FY 2021-22", 30.12, 29.67, 138.45),
        ("FY 2022-23", 34.21, 33.88, 162.34),
        ("FY 2023-24", 37.80, 37.12, 178.56),
    ]
    for i, r in enumerate(rows, 5):
        _row(ws, i, r, alt=(i%2==0))
    ws2 = wb.create_sheet("Highlights")
    ws2['A3'] = "BCCL achieved coal production of 37.80 MT in FY 2023-24."
    ws2['A4'] = "Coal dispatch by BCCL was 37.12 MT."
    ws2['A5'] = "Overburden removal was 178.56 MCM."
    _autofit(ws)
    return _xlsx_buf(wb)

def make_ministry_stats():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Monthly Stats FY2023-24"
    ws['A1'] = "Ministry of Coal — Monthly Coal Production Statistics FY 2023-24"
    ws['A1'].font = Font(bold=True, size=13)
    ws['A3'] = "During FY 2023-24, Coal India Limited achieved total coal production of 773.65 MT,"
    ws['A4'] = "registering growth of 10.03% over FY 2022-23 production of 703.21 MT."
    ws['A5'] = "Coal dispatch stood at 764.88 MT against 694.03 MT in FY 2022-23."
    ws['A6'] = "Overburden removal was 1518.22 MCM during the year."
    ws['A7'] = ""
    _hdr(ws, 8, ["Month", "CIL Production (MT)", "CIL Dispatch (MT)", "Cumulative Production (MT)"])
    months = [
        ("Apr-23", 56.22, 55.11, 56.22),
        ("May-23", 64.33, 63.22, 120.55),
        ("Jun-23", 61.45, 60.33, 181.99),
        ("Jul-23", 58.77, 57.88, 240.77),
        ("Aug-23", 62.44, 61.55, 303.21),
        ("Sep-23", 65.33, 64.22, 368.54),
        ("Oct-23", 68.22, 67.11, 436.76),
        ("Nov-23", 66.44, 65.33, 503.20),
        ("Dec-23", 72.33, 71.22, 575.53),
        ("Jan-24", 70.11, 69.00, 645.64),
        ("Feb-24", 63.22, 62.11, 708.86),
        ("Mar-24", 64.79, 63.88, 773.65),
    ]
    for i, r in enumerate(months, 9):
        _row(ws, i, r, alt=(i%2==0))
    _autofit(ws)
    return _xlsx_buf(wb)

def make_lok_sabha():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Lok Sabha Q2847"
    ws['A1'] = "LOK SABHA — UNSTARRED QUESTION NO. 2847"
    ws['A1'].font = Font(bold=True, size=13)
    ws['A2'] = "Subject: Coal Production by CIL and its Subsidiaries | Answered: 14 March 2024"
    ws['A4'] = "Coal India Limited achieved coal production of 773.65 MT in FY 2023-24."
    ws['A5'] = "BCCL produced 37.80 MT and CCL produced 81.23 MT during FY 2023-24."
    ws['A6'] = "MCL recorded its highest ever coal production of 189.44 MT in FY 2023-24."
    ws['A7'] = "Total manpower across CIL was 241398 employees as on 31 March 2024."
    ws['A8'] = ""
    _hdr(ws, 9, ["Subsidiary", "FY 2021-22 (MT)", "FY 2022-23 (MT)", "FY 2023-24 (MT)"])
    data = [
        ("ECL",       32.11,  37.22,  41.88),
        ("BCCL",      30.12,  34.21,  37.80),
        ("CCL",       65.88,  74.35,  81.23),
        ("NCL",       73.55,  85.22,  96.44),
        ("WCL",       36.22,  39.44,  45.11),
        ("SECL",     123.44, 139.22, 152.78),
        ("MCL",      155.44, 170.23, 189.44),
        ("NEC",        6.33,   6.88,   7.11),
        ("CIL Total",623.13, 703.21, 773.65),
    ]
    for i, r in enumerate(data, 10):
        _row(ws, i, r, alt=(i%2==0))
    _autofit(ws)
    return _xlsx_buf(wb)

def make_synthetic_conflict():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "SYNTHETIC - DO NOT CITE"
    ws['A1'] = "[SYNTHETIC DOCUMENT — DEMO USE ONLY — NOT AN OFFICIAL SOURCE]"
    ws['A1'].font = Font(bold=True, color="FF0000", size=13)
    ws['A2'] = "This document contains deliberately altered data to demonstrate conflict detection."
    ws['A3'] = "Product Principle 6: All synthetic data is clearly labelled. DO NOT cite this document."
    ws['A4'] = ""
    ws['A5'] = "CIL Performance Report FY 2022-23 — ALTERNATE VERSION (SYNTHETIC CONFLICT)"
    ws['A5'].font = Font(bold=True, size=12, color="CC0000")
    ws['A6'] = ""
    _hdr(ws, 7, ["Metric", "Value", "Unit", "Period", "Source Note"])
    rows = [
        ("Coal Production",    687.45, "MT",  "FY 2022-23", "SYNTHETIC: deliberately altered from 703.21 to show conflict detection"),
        ("Coal Dispatch",      694.03, "MT",  "FY 2022-23", "Unchanged — official CIL data"),
        ("Overburden Removal",1421.89, "MCM", "FY 2022-23", "Unchanged — official CIL data"),
    ]
    for i, r in enumerate(rows, 8):
        _row(ws, i, r, alt=(i%2==0))

    ws2 = wb.create_sheet("SYNTHETIC Prose")
    ws2['A1'] = "[SYNTHETIC DOCUMENT — FOR DEMO CONFLICT DEMONSTRATION ONLY]"
    ws2['A1'].font = Font(bold=True, color="FF0000")
    ws2['A3'] = "Coal India Limited achieved total coal production of 687.45 MT during FY 2022-23."
    ws2['A4'] = "Note: This figure (687.45 MT) is SYNTHETIC — the official figure is 703.21 MT."
    _autofit(ws)
    return _xlsx_buf(wb)

# ── Upload + Pipeline ──────────────────────────────────────────────────────────
XLSX_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

def upload(filename, buf):
    r = api("post", "/documents/upload",
            files={"files": (filename, buf, XLSX_TYPE)})
    if r.ok:
        docs = r.json().get("documents", [])
        if docs:
            doc_id = docs[0]["id"]
            print(f"  ✅ Uploaded '{filename}' → {doc_id[:8]}…")
            return doc_id
    return None

def wait_phase1(doc_id, timeout=90):
    for _ in range(timeout):
        r = api("get", f"/documents/{doc_id}/status")
        if r.ok:
            status = r.json().get("processing_status")
            if status == "done":
                return True
            if status == "failed":
                print(f"    ❌ Phase 1 failed")
                return False
        time.sleep(1)
    print(f"    ⚠ Phase 1 timeout")
    return False

def run_phase2(doc_id):
    r = api("post", f"/documents/{doc_id}/process-facts", json={"force": True})
    return r.ok

def wait_phase2(doc_id, timeout=120):
    for _ in range(timeout // 2):
        r = api("get", f"/documents/{doc_id}/process-facts/status")
        if r.ok:
            status = r.json().get("status")
            if status == "done":
                d = r.json()
                print(f"    ✅ Facts: {d.get('facts_extracted',0)} extracted, {d.get('facts_normalized',0)} normalized, {d.get('conflicts_found',0)} conflicts")
                return True
            if status in ("failed", "error"):
                print(f"    ❌ Phase 2 failed: {r.json().get('error','')}")
                return False
            if status == "not_started":
                return True  # No facts found but pipeline ran
        time.sleep(2)
    return False

# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*65)
print("CMPDI DEMO CORPUS SEEDER v2")
print("="*65)

queue = []

# CIL Annual Reports (6 years)
print("\n📄 CIL Annual Reports (6 fiscal years)...")
for (fy, prod, disp, ob, manpower) in CIL_YEARS:
    safe = fy.replace(" ", "_").replace("/", "-")
    fname = f"CIL_Annual_Report_{safe}.xlsx"
    buf = make_cil_annual(fy, prod, disp, ob, manpower)
    doc_id = upload(fname, buf)
    if doc_id:
        queue.append((doc_id, fname))

# MCL multi-year
print("\n📄 MCL Multi-Year Report...")
doc_id = upload("MCL_Production_FY2018_FY2024.xlsx", make_mcl_report())
if doc_id: queue.append((doc_id, "MCL"))

# BCCL multi-year
print("\n📄 BCCL Multi-Year Report...")
doc_id = upload("BCCL_Production_FY2018_FY2024.xlsx", make_bccl_report())
if doc_id: queue.append((doc_id, "BCCL"))

# Ministry of Coal Stats
print("\n📄 Ministry of Coal Monthly Stats...")
doc_id = upload("MoC_Monthly_Stats_FY2023-24.xlsx", make_ministry_stats())
if doc_id: queue.append((doc_id, "MoC"))

# Lok Sabha Q&A
print("\n📄 Lok Sabha Q2847...")
doc_id = upload("LokSabha_Q2847_Coal_Production_Mar2024.xlsx", make_lok_sabha())
if doc_id: queue.append((doc_id, "LokSabha"))

# Synthetic conflict
print("\n📄 SYNTHETIC CONFLICT document...")
doc_id = upload("SYNTHETIC_CONFLICT_CIL_FY2022-23_ALTERED.xlsx", make_synthetic_conflict())
if doc_id: queue.append((doc_id, "SYNTHETIC"))

print(f"\n✅ Uploaded {len(queue)} documents")

# Phase 1 + Phase 2 for each
print("\n⚙  Running Phase 1 + Phase 2 on all documents...")
for doc_id, label in queue:
    print(f"\n  → [{label[:30]}] {doc_id[:8]}…")
    if wait_phase1(doc_id):
        if run_phase2(doc_id):
            time.sleep(1)
    time.sleep(0.5)

print("\n⏳ Waiting for Phase 2 completion (20s buffer)...")
time.sleep(20)

print("\n📊 Phase 2 status check:")
for doc_id, label in queue:
    wait_phase2(doc_id)

# Recompute topics
print("\n🔄 Recomputing topics...")
r = api("post", "/topics/recompute")
if r.ok:
    print(f"  ✅ {r.json()}")

# ── Final Dashboard Stats ────────────────────────────────────────────────────
print("\n" + "="*65)
print("FINAL DASHBOARD STATS")
print("="*65)
r = api("get", "/dashboard/stats")
if r.ok:
    s = r.json()
    p = s.get("pipeline",{})
    e = s.get("extraction",{})
    t = s.get("trust",{})
    n = s.get("normalization",{})
    print(f"  Documents processed:   {p.get('documents_processed','?')}")
    print(f"  Pages processed:       {p.get('pages_processed','?')}")
    print(f"  Tables extracted:      {p.get('tables_extracted','?')}")
    print(f"  Text blocks extracted: {p.get('text_blocks_extracted','?')}")
    print(f"  Facts extracted:       {e.get('total_extracted_facts','?')}")
    print(f"  Facts normalized:      {n.get('total_normalized_facts','?')}")
    print(f"  Avg confidence:        {e.get('avg_extraction_confidence','?')}")
    print(f"  Open conflicts:        {t.get('open_conflicts','?')}")
    print(f"  Resolved conflicts:    {t.get('resolved_conflicts','?')}")

# Entity fact counts
print("\n" + "="*65)
print("ENTITY FACT COUNTS (for analytics/forecast selection)")
print("="*65)
r = api("get", "/entities?page_size=30")
if r.ok:
    for e in r.json().get("items",[]):
        rf = api("get", f"/facts?page_size=1&entity_id={e['id']}")
        count = rf.json().get("total","?") if rf.ok else "?"
        if str(count) != "0":
            print(f"  ★ {e['canonical_name']:35s}  facts={count}")
        else:
            print(f"    {e['canonical_name']:35s}  facts={count}")

# Facts by metric
print("\n" + "="*65)
print("FACT COUNTS BY METRIC")
print("="*65)
for metric in ["coal_production","coal_dispatch","ob_removal","manpower"]:
    rf = api("get", f"/facts?page_size=1&metric={metric}")
    count = rf.json().get("total","?") if rf.ok else "?"
    print(f"  {metric:25s}  facts={count}")

print("\n✅ Seeding complete.")
