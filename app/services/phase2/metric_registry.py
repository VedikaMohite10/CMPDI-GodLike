"""Metric registry — canonical metric names, aliases, units, and conversion rules.

This is the single source of truth for what metrics this system understands.
Nothing here involves LLM calls — pure deterministic lookup tables.
"""
from typing import Optional

# ---------------------------------------------------------------------------
# Canonical metric names (stored in normalized_facts.metric)
# ---------------------------------------------------------------------------
CANONICAL_METRICS: dict[str, str] = {
    # metric_key: human-readable label
    "coal_production":  "Coal Production",
    "coal_dispatch":    "Coal Dispatch",
    "ob_removal":       "Overburden Removal",
    "seam_depth":       "Coal Seam Depth",
    "seam_thickness":   "Coal Seam Thickness",
    "coal_grade":       "Coal Grade",
    "manpower":         "Manpower",
    "latitude":         "Latitude",
    "longitude":        "Longitude",
}

# metric_key → category
METRIC_CATEGORY: dict[str, str] = {
    "coal_production": "production",
    "coal_dispatch":   "production",
    "ob_removal":      "production",
    "seam_depth":      "survey",
    "seam_thickness":  "survey",
    "coal_grade":      "survey",
    "manpower":        "operations",
    "latitude":        "geospatial",
    "longitude":       "geospatial",
}

# Phrases that map to a canonical metric key (case-insensitive substring match)
# Longer/more-specific phrases first so they take priority over shorter ones.
METRIC_ALIASES: list[tuple[str, str]] = [
    # coal_production
    ("coal production",         "coal_production"),
    ("raw coal production",     "coal_production"),
    ("production of coal",      "coal_production"),
    ("total production",        "coal_production"),
    ("coal output",             "coal_production"),
    ("production (mt)",         "coal_production"),
    ("production(mt)",          "coal_production"),
    # coal_dispatch
    ("coal dispatch",           "coal_dispatch"),
    ("dispatch",                "coal_dispatch"),
    ("despatched",              "coal_dispatch"),
    # ob_removal
    ("overburden removal",      "ob_removal"),
    ("ob removal",              "ob_removal"),
    ("ob removed",              "ob_removal"),
    ("ob (mcm)",                "ob_removal"),
    ("ob removal (mcm)",        "ob_removal"),
    ("oe removal",              "ob_removal"),    # common OCR error
    # seam_depth
    ("coal seam depth",         "seam_depth"),
    ("seam depth",              "seam_depth"),
    ("depth",                   "seam_depth"),
    ("coal_seam_depth_m",       "seam_depth"),
    # seam_thickness
    ("seam thickness",          "seam_thickness"),
    ("thickness",               "seam_thickness"),
    ("thickness_m",             "seam_thickness"),
    # coal_grade
    ("coal grade",              "coal_grade"),
    ("grade",                   "coal_grade"),
    # manpower
    ("manpower",                "manpower"),
    ("man power",               "manpower"),
    ("employees",               "manpower"),
    ("workers",                 "manpower"),
    # geospatial
    ("latitude",                "latitude"),
    ("longitude",               "longitude"),
]

# ---------------------------------------------------------------------------
# Unit normalization lookup
# Canonical units: MT (million tonnes), MCM (million cubic metres), m (metres), %
# ---------------------------------------------------------------------------
# (raw_unit_text variants) → (canonical_unit, conversion_factor_to_canonical)
# conversion: normalized_value = raw_value * factor
UNIT_CONVERSIONS: dict[str, tuple[str, float]] = {
    # Mass — canonical: MT
    "mt":               ("MT",  1.0),
    "m.t.":             ("MT",  1.0),
    "million tonnes":   ("MT",  1.0),
    "million tonne":    ("MT",  1.0),
    "million ton":      ("MT",  1.0),
    "million tons":     ("MT",  1.0),
    "kt":               ("MT",  0.001),
    "k.t.":             ("MT",  0.001),
    "thousand tonnes":  ("MT",  0.001),
    "lakh tonnes":      ("MT",  0.1),
    "lakh tonne":       ("MT",  0.1),
    "crore tonnes":     ("MT",  10.0),
    "crore tonne":      ("MT",  10.0),
    "tonnes":           ("MT",  1e-6),    # single tonne → MT
    "tonne":            ("MT",  1e-6),
    "tons":             ("MT",  1e-6),
    "ton":              ("MT",  1e-6),
    # Volume — canonical: MCM
    "mcm":              ("MCM", 1.0),
    "m.c.m.":           ("MCM", 1.0),
    "million cubic metres": ("MCM", 1.0),
    "million cubic meters": ("MCM", 1.0),
    "bcm":              ("MCM", 1000.0),   # billion cubic metres
    "billion cubic metres": ("MCM", 1000.0),
    # Length — canonical: m
    "m":                ("m",   1.0),
    "meter":            ("m",   1.0),
    "metre":            ("m",   1.0),
    "meters":           ("m",   1.0),
    "metres":           ("m",   1.0),
    # Dimensionless
    "%":                ("%",   1.0),
    "percent":          ("%",   1.0),
    # Geospatial — no conversion
    "°n":               ("°N",  1.0),
    "°e":               ("°E",  1.0),
}


def resolve_metric(raw_text: str) -> Optional[str]:
    """Return canonical metric key for a raw header/cell string, or None."""
    if not raw_text:
        return None
    lowered = raw_text.strip().lower()
    for alias, key in METRIC_ALIASES:
        if alias in lowered:
            return key
    return None


def resolve_unit(raw_unit: str) -> Optional[tuple[str, float]]:
    """Return (canonical_unit, conversion_factor) or None if unrecognized.

    Caller computes: normalized_value = raw_numeric * factor
    """
    if not raw_unit:
        return None
    key = raw_unit.strip().lower()
    return UNIT_CONVERSIONS.get(key)


# Plausible value ranges per metric (for validation_engine)
# (min_inclusive, max_inclusive) — None means unbounded in that direction
METRIC_RANGES: dict[str, tuple[Optional[float], Optional[float]]] = {
    "coal_production": (0.001, 500.0),   # MT — single mine: 0.001, largest mine ~50 MT
    "coal_dispatch":   (0.001, 500.0),
    "ob_removal":      (0.001, 5000.0),  # MCM
    "seam_depth":      (1.0,   2000.0),  # m
    "seam_thickness":  (0.1,   50.0),    # m
    "latitude":        (6.0,   37.0),    # India's lat range
    "longitude":       (68.0,  98.0),    # India's lon range
    "manpower":        (1,     200000),
}
