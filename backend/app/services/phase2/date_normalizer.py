"""Date/period normalizer — deterministic, no LLM.

Converts Indian coal-report date strings to (period_start, period_end, label, method).

Supported formats (in priority order):
1. FY YYYY-YY  / FY YYYY-YYYY  → April 1 of year1 to March 31 of year2
2. YYYY-YY / YYYY-YYYY         → same FY interpretation if delta ≤ 1
3. YYYY/YY / YYYY/YYYY         → same
4. April–March YYYY            → FY ending in YYYY
5. Q[1-4] YYYY                 → calendar quarter
6. DD/MM/YYYY                  → single date
7. YYYY                        → calendar year Jan 1 – Dec 31
8. Month YYYY                  → first/last of that month
"""
import re
from calendar import monthrange
from datetime import date
from typing import Optional

# Month abbreviation→number (English)
_MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4,
    "may": 5, "jun": 6, "jul": 7, "aug": 8,
    "sep": 9, "oct": 10, "nov": 11, "dec": 12,
    "january": 1, "february": 2, "march": 3, "april": 4,
    "june": 6, "july": 7, "august": 8, "september": 9,
    "october": 10, "november": 11, "december": 12,
}


def _fy(year1: int) -> tuple[date, date]:
    """Indian FY: April 1 year1 → March 31 year1+1."""
    return date(year1, 4, 1), date(year1 + 1, 3, 31)


def parse_date(raw: str) -> tuple[Optional[date], Optional[date], str, str]:
    """Parse raw date/period text.

    Returns: (period_start, period_end, period_label, parse_method)
    All fields are None / 'unresolved' if parsing fails.
    """
    if not raw:
        return None, None, raw or "", "unresolved"

    s = raw.strip()
    label = s

    # 1 & 2. FY YYYY-YY or YYYY-YY or YYYY-YYYY
    m = re.match(
        r"(?:fy\s*)?(\d{4})[-/](\d{2,4})", s, re.IGNORECASE
    )
    if m:
        y1 = int(m.group(1))
        y2_raw = m.group(2)
        y2 = int(y2_raw) if len(y2_raw) == 4 else int(str(y1)[:2] + y2_raw)
        if y2 == y1 + 1:
            start, end = _fy(y1)
            return start, end, label, "fy_pattern"
        if y2 == y1:
            # Same year → treat as calendar year
            return date(y1, 1, 1), date(y1, 12, 31), label, "year_only"

    # 3. "April-March YYYY" or "Apr-Mar YYYY"
    m = re.match(r"(?:apr(?:il)?[-–]mar(?:ch)?\s*)(\d{4})", s, re.IGNORECASE)
    if m:
        fy_end_year = int(m.group(1))
        start, end = _fy(fy_end_year - 1)
        return start, end, label, "fy_pattern"

    # 4. Q1-Q4 YYYY
    m = re.match(r"Q([1-4])\s*(\d{4})", s, re.IGNORECASE)
    if m:
        q, year = int(m.group(1)), int(m.group(2))
        qstart_month = (q - 1) * 3 + 1
        qend_month   = q * 3
        last_day = monthrange(year, qend_month)[1]
        return date(year, qstart_month, 1), date(year, qend_month, last_day), label, "quarter"

    # 5. DD/MM/YYYY or DD-MM-YYYY
    m = re.match(r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})", s)
    if m:
        try:
            d = date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
            return d, d, label, "exact"
        except ValueError:
            pass

    # 6. YYYY alone (4-digit year)
    m = re.fullmatch(r"(\d{4})", s)
    if m:
        y = int(m.group(1))
        return date(y, 1, 1), date(y, 12, 31), label, "year_only"

    # 7. Month YYYY
    m = re.match(r"([a-z]+)\s+(\d{4})", s, re.IGNORECASE)
    if m:
        mon_str = m.group(1).lower()
        mon_num = _MONTHS.get(mon_str)
        year    = int(m.group(2))
        if mon_num:
            last_day = monthrange(year, mon_num)[1]
            return date(year, mon_num, 1), date(year, mon_num, last_day), label, "month_year"

    return None, None, label, "unresolved"
