"""Utility: safe filename sanitisation."""
import re
import unicodedata


def safe_filename(filename: str) -> str:
    """Normalise a filename so it's safe to store and display.

    - Strips path traversal characters
    - Removes or replaces non-ASCII characters
    - Collapses whitespace to underscores
    """
    # Normalise Unicode
    filename = unicodedata.normalize("NFKD", filename)
    filename = filename.encode("ascii", "ignore").decode("ascii")
    # Strip path separators
    filename = filename.replace("/", "_").replace("\\", "_")
    # Collapse spaces
    filename = re.sub(r"\s+", "_", filename)
    # Remove any remaining dangerous characters
    filename = re.sub(r"[^\w.\-]", "", filename)
    return filename or "unnamed_file"
