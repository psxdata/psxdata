"""Reliability tests for RealtimeScraper — mocked network, no real HTTP calls."""
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
import requests

from psxdata.scrapers.realtime import RealtimeScraper

pytestmark = pytest.mark.reliability

FIXTURE_MAIN = (Path(__file__).parent.parent / "fixtures" / "trading_board_REG_main.html").read_text(encoding="utf-8")
FIXTURE_BNB = (Path(__file__).parent.parent / "fixtures" / "trading_board_REG_bnb.html").read_text(encoding="utf-8")


def _mock_response(text: str, status_code: int = 200) -> MagicMock:
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status_code
    resp.text = text
    return resp


class TestRealtimeScraper:
    def test_reg_main_returns_price_columns(self):
        scraper = RealtimeScraper()
        with patch.object(scraper._session, "request", return_value=_mock_response(FIXTURE_MAIN)):
            df = scraper.fetch("REG", "main")
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0
        assert "symbol" in df.columns

    def test_bnb_returns_yield_columns(self):
        """BNB board schema includes yield columns alongside standard price columns."""
        scraper = RealtimeScraper()
        with patch.object(scraper._session, "request", return_value=_mock_response(FIXTURE_BNB)):
            df = scraper.fetch("REG", "bnb")
        assert isinstance(df, pd.DataFrame)
        if len(df) > 0:
            # BNB board must have at least one yield column
            bnb_cols = set(df.columns)
            assert bnb_cols & {"bid_yield", "offer_yield", "lty", "ldcy"}, \
                f"BNB board missing yield columns, got: {bnb_cols}"

    def test_reg_main_has_price_columns_not_yield(self):
        """REG/main board schema has price columns, not yield columns."""
        scraper = RealtimeScraper()
        with patch.object(scraper._session, "request", return_value=_mock_response(FIXTURE_MAIN)):
            df = scraper.fetch("REG", "main")
        if len(df) > 0:
            assert "bid_yield" not in df.columns, "REG/main board should not have bid_yield"

    def test_empty_html_returns_empty_dataframe(self):
        scraper = RealtimeScraper()
        with patch.object(scraper._session, "request", return_value=_mock_response("<html></html>")):
            df = scraper.fetch("REG", "main")
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0

    def test_malformed_html_no_th_returns_empty_dataframe(self):
        bad_html = "<html><body><table><tbody><tr><td>ENGRO</td></tr></tbody></table></body></html>"
        scraper = RealtimeScraper()
        with patch.object(scraper._session, "request", return_value=_mock_response(bad_html)):
            df = scraper.fetch("REG", "main")
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0


class TestBoardBadges:
    def test_board_without_badges_still_has_string_columns(self):
        from psxdata.scrapers.realtime import RealtimeScraper

        scraper = RealtimeScraper()
        html = (Path(__file__).parent.parent / "fixtures" / "trading_board_reg_gem.html").read_text(encoding="utf-8")
        with patch.object(scraper._session, "request", return_value=_mock_response(html)):
            df = scraper.fetch("REG", "gem")
        if not df.empty:
            assert str(df["ex_flag"].dtype) == "string"
            assert df["ex_flag"].isna().all()
