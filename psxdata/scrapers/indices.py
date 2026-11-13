"""IndicesScraper — constituent data for a single PSX index.

Endpoint:  GET https://dps.psx.com.pk/indices/{name}
Method:    GET
Mode:      requests + BeautifulSoup (plain HTTP AJAX)

18 valid index names: see constants.INDEX_NAMES

Quirk:     The 10th column varies by index:
           - Most indices:  FREEFLOAT (M)  → freefloat_m
           - Some indices:  SHARES (M)     → shares_m
           Headers are always extracted dynamically from <th> tags.
           Never hardcode column positions.
"""
from __future__ import annotations

import logging

import pandas as pd

from psxdata.parsers.html import parse_html_table, string_badges
from psxdata.parsers.normalizers import coerce_numeric
from psxdata.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)


class IndicesScraper(BaseScraper):
    """Fetch constituent data for a single PSX index."""

    def fetch(self, name: str) -> pd.DataFrame:
        """Fetch index constituents for the named index.

        Args:
            name: Index name, e.g. "KSE100", "ALLSHR", "KSE30".
                  See constants.INDEX_NAMES for the full list.

        Returns:
            DataFrame with columns including: symbol, current_index, idx_weight,
            idx_point, market_cap_m, and either freefloat_m or shares_m
            (depends on the index).
            Empty DataFrame if PSX returns no data.

        Raises:
            PSXConnectionError: Network failure after retries.
            PSXServerError: 5xx after retries.
        """
        logger.debug("Fetching index constituents for %s", name)
        url = self._build_url("indices") + f"/{name}"
        resp = self._request("GET", url)
        rows = parse_html_table(resp.text, badges=True)

        if not rows:
            logger.warning("Index %s returned no data", name)
            return pd.DataFrame()

        df = pd.DataFrame(rows)

        df = string_badges(df)
        logger.debug("Parsed %d rows for index %s", len(df), name)

        numeric_cols = (
            "current_index", "idx_weight", "idx_point",
            "market_cap_m", "freefloat_m", "shares_m",
        )
        for col in numeric_cols:
            if col in df.columns:
                df[col] = df[col].apply(coerce_numeric)

        return df
