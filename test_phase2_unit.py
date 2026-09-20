#!/usr/bin/env python3
"""
Phase 2 Unit Tests — deterministic services only (no server, no DB needed).
Tests: metric_registry, unit_normalizer, date_normalizer, heuristic_text_extractor.

Run: python3 test_phase2_unit.py
"""
import sys

PASS = "\033[92m✓\033[0m"
FAIL = "\033[91m✗\033[0m"
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


# ─── Metric Registry ─────────────────────────────────────────────────────────
section("Metric Registry")
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from app.services.phase2.metric_registry import resolve_metric, resolve_unit

check("resolve_metric('Production (MT)') → coal_production",
      resolve_metric("Production (MT)") == "coal_production")
check("resolve_metric('coal output') → coal_production",
      resolve_metric("coal output") == "coal_production")
check("resolve_metric('OB Removal (MCM)') → ob_removal",
      resolve_metric("OB Removal (MCM)") == "ob_removal")
check("resolve_metric('seam depth') → seam_depth",
      resolve_metric("seam depth") == "seam_depth")
check("resolve_metric('dispatch') → coal_dispatch",
      resolve_metric("dispatch") == "coal_dispatch")
check("resolve_metric('manpower') → manpower",
      resolve_metric("manpower") == "manpower")
check("resolve_metric('') → None",
      resolve_metric("") is None)
check("resolve_metric('irrelevant header') → None",
      resolve_metric("irrelevant header") is None)

check("resolve_unit('MT') → ('MT', 1.0)",
      resolve_unit("MT") == ("MT", 1.0))
check("resolve_unit('million tonnes') → ('MT', 1.0)",
      resolve_unit("million tonnes") == ("MT", 1.0))
check("resolve_unit('KT') → ('MT', 0.001)",
      resolve_unit("KT") == ("MT", 0.001))
check("resolve_unit('lakh tonnes') → ('MT', 0.1)",
      resolve_unit("lakh tonnes") == ("MT", 0.1))
check("resolve_unit('MCM') → ('MCM', 1.0)",
      resolve_unit("MCM") == ("MCM", 1.0))
check("resolve_unit('BCM') → ('MCM', 1000.0)",
      resolve_unit("BCM") == ("MCM", 1000.0))
check("resolve_unit('m') → ('m', 1.0)",
      resolve_unit("m") == ("m", 1.0))
check("resolve_unit('XYZ') → None",
      resolve_unit("XYZ") is None)

# ─── Unit Normalizer ─────────────────────────────────────────────────────────
section("Unit Normalizer")
from app.services.phase2.unit_normalizer import parse_numeric, normalize_unit

check("parse_numeric('15.4') → 15.4",        parse_numeric("15.4") == 15.4)
check("parse_numeric('1,234.5') → 1234.5",   parse_numeric("1,234.5") == 1234.5)
check("parse_numeric('(5.2)') → -5.2",       parse_numeric("(5.2)") == -5.2)
check("parse_numeric('15.4%') → 15.4",       parse_numeric("15.4%") == 15.4)
check("parse_numeric('') → None",            parse_numeric("") is None)
check("parse_numeric('N/A') → None",         parse_numeric("N/A") is None)
check("parse_numeric('abc') → None",         parse_numeric("abc") is None)
check("parse_numeric('2.1') → 2.1",          abs(parse_numeric("2.1") - 2.1) < 1e-9)

v, u, note, notes = normalize_unit("2.1", "MT")
check("normalize_unit('2.1', 'MT') value=2.1", abs(v - 2.1) < 1e-9)
check("normalize_unit('2.1', 'MT') unit='MT'", u == "MT")
check("normalize_unit('2.1', 'MT') no conversion note", "unit_conversion" not in notes)

v2, u2, note2, notes2 = normalize_unit("500", "KT")
check("normalize_unit('500', 'KT') → 0.5 MT", abs(v2 - 0.5) < 1e-9)
check("normalize_unit('500', 'KT') unit='MT'", u2 == "MT")
check("normalize_unit('500', 'KT') has conversion note", "unit_conversion" in notes2)

v3, u3, _, notes3 = normalize_unit("abc", "MT")
check("normalize_unit('abc', 'MT') value=None", v3 is None)
check("normalize_unit('abc', 'MT') parse_error in notes", "parse_error" in notes3)

v4, u4, _, notes4 = normalize_unit("5.2", "UNKNOWN_UNIT")
check("normalize_unit('5.2', 'UNKNOWN_UNIT') unit=None", u4 is None)
check("normalize_unit('5.2', 'UNKNOWN_UNIT') unrecognized in notes", "unit_unrecognized" in notes4)

v5, u5, _, notes5 = normalize_unit("100", "lakh tonnes")
check("normalize_unit('100', 'lakh tonnes') → 10.0 MT", abs(v5 - 10.0) < 1e-9)

# ─── Date Normalizer ─────────────────────────────────────────────────────────
section("Date Normalizer")
from datetime import date
from app.services.phase2.date_normalizer import parse_date

def fy_check(raw, expected_start, expected_end, method):
    s, e, lbl, m = parse_date(raw)
    ok = s == expected_start and e == expected_end and m == method
    check(f"parse_date({raw!r})", ok, f"got s={s} e={e} m={m}")

fy_check("FY 2022-23", date(2022, 4, 1), date(2023, 3, 31), "fy_pattern")
fy_check("2022-23",    date(2022, 4, 1), date(2023, 3, 31), "fy_pattern")
fy_check("2022/23",    date(2022, 4, 1), date(2023, 3, 31), "fy_pattern")
fy_check("2023-2024",  date(2023, 4, 1), date(2024, 3, 31), "fy_pattern")
fy_check("2024",       date(2024, 1, 1), date(2024, 12, 31), "year_only")

s, e, lbl, m = parse_date("Q1 2023")
check("parse_date('Q1 2023') → Jan-Mar 2023", s == date(2023, 1, 1) and e == date(2023, 3, 31))

s, e, lbl, m = parse_date("Q3 2022")
check("parse_date('Q3 2022') → Jul-Sep 2022", s == date(2022, 7, 1) and e == date(2022, 9, 30))

s, e, lbl, m = parse_date("15/04/2022")
check("parse_date('15/04/2022') → exact", s == date(2022, 4, 15) and m == "exact")

s, e, lbl, m = parse_date("March 2023")
check("parse_date('March 2023') → March 2023", s == date(2023, 3, 1) and e == date(2023, 3, 31))

s, e, lbl, m = parse_date("")
check("parse_date('') → unresolved", s is None and m == "unresolved")
s, e, lbl, m = parse_date("JUNK TEXT")
check("parse_date('JUNK TEXT') → unresolved", s is None and m == "unresolved")

# ─── Heuristic Text Extractor ────────────────────────────────────────────────
section("Heuristic Text Extractor")
from app.services.phase2.heuristic_text_extractor import extract_from_text

text1 = "Total coal production during FY 2022-23 was 15.4 MT."
facts = extract_from_text(text1, date_text="2022-23")
check("Extracts coal_production from prose", any(f["raw_metric_text"] == "coal_production" for f in facts),
      f"got {[f['raw_metric_text'] for f in facts]}")
check("Extracted value = '15.4'", any(f["raw_value"] == "15.4" for f in facts))
check("Extracted unit = 'MT'", any(f["raw_unit_text"] and "MT" in f["raw_unit_text"] for f in facts))

text2 = "OB removal was 45.2 MCM during Q2 2023."
facts2 = extract_from_text(text2)
check("Extracts ob_removal from prose", any(f["raw_metric_text"] == "ob_removal" for f in facts2))

text3 = "The coal seam depth at this location is 350 m."
facts3 = extract_from_text(text3)
check("Extracts seam_depth from prose", any(f["raw_metric_text"] == "seam_depth" for f in facts3))

# No extraction from empty / irrelevant text
facts_empty = extract_from_text("")
check("Empty text → []", facts_empty == [])
facts_irrel = extract_from_text("The meeting was held on Monday.")
check("Irrelevant text → []", facts_irrel == [])

# ─── Summary ─────────────────────────────────────────────────────────────────
section("UNIT TEST SUMMARY")
passed = sum(1 for _, ok in results if ok)
failed = sum(1 for _, ok in results if not ok)
print(f"  Passed: {passed}/{len(results)}")
if failed:
    print(f"\n  FAILED ({failed}):")
    for lbl, ok in results:
        if not ok:
            print(f"    {FAIL} {lbl}")
print()
sys.exit(0 if failed == 0 else 1)
