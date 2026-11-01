"""Dynamic HTML table parser for PSX pages.

Extracts table data without assuming fixed column positions. Headers are
mapped via COLUMN_MAP; unknown headers fall back to normalize_column_name
with a logged warning.
"""
from __future__ import annotations

import logging
import re

from bs4 import BeautifulSoup, Tag

from psxdata.constants import COLUMN_MAP
from psxdata.parsers.normalizers import normalize_column_name

logger = logging.getLogger(__name__)


def extract_table_headers(table: Tag) -> list[str]:
    """Extract and normalise column headers from a single table element.

    Applies COLUMN_MAP first; unknown headers fall back to
    normalize_column_name with a warning logged.

    Args:
        table: A single <table> BeautifulSoup element.

    Returns:
        List of normalised column name strings.
    """
    th_tags = table.find_all("th")
    if not th_tags:
        return []
    headers: list[str] = []
    for th in th_tags:
        raw = th.get_text(strip=True)
        if raw in COLUMN_MAP:
            headers.append(COLUMN_MAP[raw])
        else:
            normalised = normalize_column_name(raw)
            if raw:
                logger.warning(
                    "Unknown PSX column header %r — using fallback name %r. "
                    "Add to constants.COLUMN_MAP if this is a new PSX column.",
                    raw,
                    normalised,
                )
            headers.append(normalised)
    return headers


_ABBREVIATED_NUMBER = re.compile(r"^-?[\d.,]+\s*[KMBT]$")


def _cell_value(td: Tag, headers: list[str], index: int) -> str:
    """Return the cell's text, preferring PSX's exact ``data-order`` value where
    the visible text is lossy: abbreviated numbers ("167.7B") and symbol cells,
    which can carry a tag badge ("BAHL" + "XD") that pollutes the text.
    """
    text = td.get_text(strip=True)
    exact = td.get("data-order")
    if exact is None or index >= len(headers):
        return text
    if headers[index] == "symbol" or _ABBREVIATED_NUMBER.match(text):
        return str(exact).strip()
    return text


def parse_table_rows(table: Tag, headers: list[str]) -> list[dict[str, str]]:
    """Map <tr><td> rows to dicts keyed by normalised header name.

    Rows with a different cell count than headers get a warning logged but
    are still returned with available cells mapped.

    Args:
        table: A single <table> BeautifulSoup element.
        headers: Normalised column names from extract_table_headers.

    Returns:
        List of row dicts mapping header name -> raw cell text.
    """
    rows: list[dict[str, str]] = []
    tbody = table.find("tbody")
    tr_tags = tbody.find_all("tr") if tbody else table.find_all("tr")

    for tr in tr_tags:
        cells = [_cell_value(td, headers, i) for i, td in enumerate(tr.find_all("td"))]
        if not cells:
            continue
        if len(cells) != len(headers):
            logger.warning(
                "Row has %d cells but expected %d — partial mapping applied",
                len(cells),
                len(headers),
            )
        row = {headers[i]: cells[i] for i in range(min(len(headers), len(cells)))}
        rows.append(row)
    return rows


def parse_html_table(html: str) -> list[dict[str, str]]:
    """Parse the first HTML table in html, returning rows as normalised dicts.

    Both headers and rows are scoped to the same first <table> element,
    preventing column/row mismatch on pages with multiple tables.
    Returns an empty list for empty or malformed HTML with a warning logged.
    All values are raw strings — callers apply coerce_numeric / parse_date_safely.

    Args:
        html: Raw HTML string from a PSX endpoint response.

    Returns:
        List of row dicts. Each dict maps normalised column name -> raw string value.
    """
    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table")
    if not table:
        logger.warning("No table found in HTML — returning empty result")
        return []
    headers = extract_table_headers(table)
    if not headers:
        logger.warning("No table headers found in HTML — returning empty result")
        return []
    return parse_table_rows(table, headers)


def parse_tables_by_heading(html: str) -> dict[str, list[dict[str, str]]]:
    """Parse multiple HTML tables keyed by the preceding <h2> heading.

    Used by debt_market.py and eligible_scrips.py. Each table is associated
    with the nearest preceding <h2> sibling. Falls back to "table_N" (0-indexed)
    if no preceding <h2> is found.

    Args:
        html: Raw HTML string from a PSX endpoint response.

    Returns:
        Dict mapping normalized heading -> list of row dicts.
        Empty dict if no tables found.
    """
    soup = BeautifulSoup(html, "lxml")
    tables = soup.find_all("table")
    if not tables:
        return {}

    result: dict[str, list[dict[str, str]]] = {}
    for i, table in enumerate(tables):
        # Walk backwards through previous siblings to find nearest <h2>
        heading: str | None = None
        for sibling in table.find_previous_siblings():
            if sibling.name == "h2":
                heading = normalize_column_name(sibling.get_text(strip=True))
                break
            if sibling.name == "table":
                break  # hit another table before finding a heading

        key = heading if heading else f"table_{i}"
        headers = extract_table_headers(table)
        if not headers:
            logger.warning("No headers found for table with key %r — skipping", key)
            continue
        rows = parse_table_rows(table, headers)
        result[key] = rows

    return result
