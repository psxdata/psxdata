"""Reliability tests for ScreenerScraper — mocked network, no real HTTP calls."""
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
import requests

from psxdata.scrapers.screener import ScreenerScraper

pytestmark = pytest.mark.reliability

FIXTURE = (Path(__file__).parent.parent / "fixtures" / "screener.html").read_text(encoding="utf-8")


def _mock_response(text: str, status_code: int = 200) -> MagicMock:
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status_code
    resp.text = text
    return resp


class TestScreenerScraper:
    def test_returns_dataframe_with_key_columns(self):
        scraper = ScreenerScraper()
        with patch.object(scraper._session, "request", return_value=_mock_response(FIXTURE)):
            df = scraper.fetch()
        assert isinstance(df, pd.DataFrame)
        for col in ("symbol", "sector", "listed_in"):
            assert col in df.columns, f"Missing column: {col}"

    def test_returns_non_empty_result(self):
        scraper = ScreenerScraper()
        with patch.object(scraper._session, "request", return_value=_mock_response(FIXTURE)):
            df = scraper.fetch()
        assert len(df) > 0

    def test_sector_column_is_numeric_code(self):
        """Sector column must NOT be enriched — raw numeric codes only."""
        scraper = ScreenerScraper()
        with patch.object(scraper._session, "request", return_value=_mock_response(FIXTURE)):
            df = scraper.fetch()
        # Sector values should be numeric (or NaN), not sector name strings
        non_null = df["sector"].dropna()
        assert len(non_null) > 0
        pd.to_numeric(non_null, errors="raise")  # raises if any value is a string name

    def test_change_pct_column_is_numeric(self):
        """change_pct must be coerced to float, not left as a raw percent string."""
        scraper = ScreenerScraper()
        with patch.object(scraper._session, "request", return_value=_mock_response(FIXTURE)):
            df = scraper.fetch()
        non_null = df["change_pct"].dropna()
        assert len(non_null) > 0
        assert pd.api.types.is_numeric_dtype(df["change_pct"])

    def test_empty_html_returns_empty_dataframe(self):
        scraper = ScreenerScraper()
        with patch.object(scraper._session, "request", return_value=_mock_response("<html></html>")):
            df = scraper.fetch()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0

    def test_malformed_html_no_th_returns_empty_dataframe(self):
        bad_html = "<html><body><table><tbody><tr><td>ENGRO</td></tr></tbody></table></body></html>"
        scraper = ScreenerScraper()
        with patch.object(scraper._session, "request", return_value=_mock_response(bad_html)):
            df = scraper.fetch()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0


class TestScreenerPeRatio:
    def _fetch(self, rows):
        scraper = ScreenerScraper()
        with (
            patch.object(scraper._session, "request", return_value=_mock_response("<html></html>")),
            patch("psxdata.scrapers.screener.parse_html_table", return_value=rows),
        ):
            return scraper.fetch().set_index("symbol")

    def test_zero_pe_becomes_nan(self):
        """PSX shows 0.00 when there is no meaningful P/E (e.g. losses); 0 would
        rank as the cheapest stock, so it's returned as NaN."""
        df = self._fetch([
            {"symbol": "LOSS", "pe_ratio": "0.00", "dividend_yield": "0.00", "price": "10"},
            {"symbol": "PROF", "pe_ratio": "8.50", "dividend_yield": "0.00", "price": "20"},
        ])
        assert pd.isna(df.loc["LOSS", "pe_ratio"])
        assert df.loc["PROF", "pe_ratio"] == 8.5

    def test_zero_dividend_yield_is_kept(self):
        """A 0 dividend yield is real (no dividend), unlike a 0 P/E."""
        df = self._fetch([{"symbol": "LOSS", "pe_ratio": "0.00", "dividend_yield": "0.00", "price": "10"}])
        assert df.loc["LOSS", "dividend_yield"] == 0.0
