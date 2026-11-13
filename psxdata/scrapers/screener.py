"""ScreenerScraper — full stock screener table from PSX.

Endpoint:  GET https://dps.psx.com.pk/screener
Method:    GET
Mode:      requests + BeautifulSoup (plain HTTP)

Quirk:     SECTOR column contains a numeric sector code, not a name.
           No enrichment is done here — join to sector names via SymbolsScraper
           at the API layer.
"""
from __future__ import annotations

import logging

import pandas as pd

from psxdata.parsers.html import parse_html_table, string_badges
from psxdata.parsers.normalizers import coerce_numeric
from psxdata.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)


class ScreenerScraper(BaseScraper):
    """Fetch the PSX stock screener table."""

    def fetch(self) -> pd.DataFrame:
        """Fetch the full screener table.

        Returns:
            DataFrame with columns including: symbol, sector, listed_in,
            market_cap, price, pe_ratio, dividend_yield, free_float,
            volume_avg_30d, change_1y_pct.
            sector column contains raw numeric codes — not enriched.
            pe_ratio is NaN where PSX shows 0.00 (no meaningful P/E).
            Empty DataFrame if PSX returns no table data.

        Raises:
            PSXConnectionError: Network failure after retries.
            PSXServerError: 5xx after retries.
        """
        logger.debug("Fetching screener data")
        resp = self._get("screener")
        rows = parse_html_table(resp.text, badges=True)

        if not rows:
            logger.warning("Screener returned no data")
            return pd.DataFrame()

        df = pd.DataFrame(rows)

        df = string_badges(df)
        logger.debug("Parsed %d screener rows", len(df))

        numeric_cols = ("market_cap", "price", "pe_ratio", "dividend_yield",
                        "free_float", "volume_avg_30d", "change_pct", "change_1y_pct", "sector")
        for col in numeric_cols:
            if col in df.columns:
                df[col] = df[col].apply(coerce_numeric)

        # PSX shows P/E 0.00 when there is no meaningful P/E (e.g. losses).
        # A 0 would sort as the cheapest stock, so return it as missing.
        # (A 0 dividend yield is real: the company pays none.)
        if "pe_ratio" in df.columns:
            df["pe_ratio"] = df["pe_ratio"].mask(df["pe_ratio"] == 0)

        return df
