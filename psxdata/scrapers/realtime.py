"""RealtimeScraper — live trading board data for a single market/board combination.

Endpoint:  GET https://dps.psx.com.pk/trading-board/{market}/{board}
Method:    GET
Mode:      requests + BeautifulSoup (plain HTTP AJAX)

One call returns one (market, board) combination. Call in a loop for multiple.

Valid markets: REG, ODL, DFC, SQR, CSF  (see constants.MARKETS)
Valid boards:  main, gem, bnb            (see constants.BOARDS)

Quirk:     BNB board returns yield columns (bid_yield, offer_yield, lty, ldcy)
           alongside standard price columns (bid_price, offer_price).
           Both schemas are handled by COLUMN_MAP — no special-casing needed.
"""
from __future__ import annotations

import logging

import pandas as pd

from psxdata.parsers.html import parse_html_table, string_badges
from psxdata.parsers.normalizers import coerce_numeric
from psxdata.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)


class RealtimeScraper(BaseScraper):
    """Fetch live trading board data for one (market, board) combination."""

    def fetch(self, market: str, board: str) -> pd.DataFrame:
        """Fetch the trading board for a specific market and board.

        Args:
            market: Market code — one of REG, ODL, DFC, SQR, CSF.
            board:  Board code — one of main, gem, bnb.

        Returns:
            DataFrame with trading data. Columns vary by board:
            - main/gem: symbol, ldcp, current, change, change_pct, volume, ...
            - bnb: symbol, bid_yield, offer_yield, ltp, lty, ldcy, ...
            Empty DataFrame if the board has no active trades.

        Raises:
            PSXConnectionError: Network failure after retries.
            PSXServerError: 5xx after retries.
        """
        logger.debug("Fetching trading board: market=%s board=%s", market, board)
        url = self._build_url("trading_board") + f"/{market}/{board}"
        resp = self._request("GET", url)
        rows = parse_html_table(resp.text, badges=True)

        if not rows:
            logger.warning("Trading board %s/%s returned no data", market, board)
            return pd.DataFrame()

        df = pd.DataFrame(rows)

        df = string_badges(df)
        logger.debug("Parsed %d rows for %s/%s", len(df), market, board)

        numeric_cols = (
            "ldcp", "current", "change", "change_pct", "volume", "turnover",
            "bid_vol", "bid_price", "offer_vol", "offer_price",
            "bid_yield", "offer_yield", "ltp", "lty", "ldcy",
        )
        for col in numeric_cols:
            if col in df.columns:
                df[col] = df[col].apply(coerce_numeric)

        return df
