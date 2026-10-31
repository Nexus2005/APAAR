"""Column mapping: alias dictionary + RapidFuzz, always human-confirmed."""

from __future__ import annotations

import re
from datetime import date, datetime
from pathlib import Path

import yaml
from rapidfuzz import fuzz

from app.core.config import PROJECT_ROOT

ALIAS_PATH = PROJECT_ROOT / "config" / "column_aliases.yaml"

_ALIAS_CACHE: dict | None = None


def alias_config() -> dict:
    global _ALIAS_CACHE
    if _ALIAS_CACHE is None:
        with ALIAS_PATH.open("r", encoding="utf-8") as fh:
            _ALIAS_CACHE = yaml.safe_load(fh)["fields"]
    return _ALIAS_CACHE


def norm_header(value: str) -> str:
    return re.sub(r"[^a-z0-9% ]", " ", (value or "").lower()).strip()


def suggest_mapping(headers: list[str]) -> dict:
    """Return {canonical_field: {source_column, confidence}} using aliases + fuzzy."""
    fields = alias_config()
    used: set[str] = set()
    suggestions: dict = {}
    normalised = [(h, norm_header(h)) for h in headers]

    for canonical, meta in fields.items():
        best: tuple[str, float] | None = None
        for raw, norm in normalised:
            if raw in used or not norm:
                continue
            if norm == canonical.replace("_", " ") or norm in [a.lower() for a in meta["aliases"]]:
                score = 100.0
            else:
                score = max(
                    fuzz.token_sort_ratio(norm, alias) for alias in meta["aliases"] + [canonical]
                )
            if score >= 62 and (best is None or score > best[1]):
                best = (raw, float(score))
        if best:
            used.add(best[0])
            suggestions[canonical] = {
                "source_column": best[0],
                "confidence": round(best[1] / 100, 4),
            }
        elif meta.get("required"):
            suggestions[canonical] = {"source_column": None, "confidence": 0.0}

    # Suggest leftovers as unknown so the UI can show them as unmapped.
    suggestions["_unmapped"] = [h for h in headers if h not in used]
    return suggestions


def mapping_is_complete(mapping: dict) -> tuple[bool, list[str]]:
    missing = [
        canonical
        for canonical, meta in alias_config().items()
        if meta.get("required") and not (mapping.get(canonical) or {}).get("source_column")
    ]
    return (not missing, missing)


DATE_FORMATS = ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y", "%d %b %Y", "%b %d %Y", "%d-%b-%Y")


def parse_date(value: object) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text:
        return None
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def parse_float(value: object) -> float | None:
    try:
        if value is None or str(value).strip() == "":
            return None
        return float(str(value).replace("%", "").strip())
    except ValueError:
        return None


SEAT_ALIASES = {
    "regular": "regular",
    "general": "regular",
    "state quota": "regular",
    "supernumerary": "supernumerary",
    "sn": "supernumerary",
    "nri": "nri",
    "oci": "oci",
    "fn": "fn",
    "foreign national": "fn",
    "foreign": "fn",
    "tfw": "tfw",
    "tuition fee waiver": "tfw",
}


def normalise_category(value: object) -> str:
    key = str(value or "").strip().lower()
    return SEAT_ALIASES.get(key, key or "regular")


def normalise_apaar_status(value: object) -> str:
    key = str(value or "").strip().lower()
    if key in {"pending", "declined"}:
        return key
    return "provided"


def read_table(filename: str, data: bytes) -> tuple[list[str], list[list[object]]]:
    """Read CSV or XLSX bytes safely (no eval, no macros)."""
    suffix = Path(filename).suffix.lower()
    if suffix == ".xlsx":
        import io

        from openpyxl import load_workbook

        wb = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
        ws = wb.active
        rows = [list(r) for r in ws.iter_rows(values_only=True)]
        if not rows:
            return [], []
        headers = [str(h).strip() if h is not None else "" for h in rows[0]]
        return headers, [r for r in rows[1:] if any(c not in (None, "") for c in r)]
    text = data.decode("utf-8-sig", errors="replace")
    import csv
    import io

    reader = csv.reader(io.StringIO(text))
    rows = [r for r in reader]
    if not rows:
        return [], []
    headers = [h.strip() for h in rows[0]]
    return headers, [r for r in rows[1:] if any(str(c).strip() for c in r)]
