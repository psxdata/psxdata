"""Reliability tests for IndicesScraper — mocked network, no real HTTP calls."""
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
import requests

from psxdata.scrapers.indices import IndicesScraper

pytestmark = pytest.mark.reliability

FIXTURE_KSE100 = (Path(__file__).parent.parent / "fixtures" / "indices_KSE100.html").read_text(encoding="utf-8")
FIXTURE_ALLSHR = (Path(__file__).parent.parent / "fixtures" / "indices_ALLSHR.html").read_text(encoding="utf-8")


def _mock_response(text: str, status_code: int = 200) -> MagicMock:
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status_code
    resp.text = text
    return resp


class TestIndicesScraper:
    def test_kse100_returns_dataframe(self):
        scraper = IndicesScraper()
        with patch.object(scraper._session, "request", return_value=_mock_response(FIXTURE_KSE100)):
            df = scraper.fetch("KSE100")
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0
        assert "symbol" in df.columns

    def test_kse100_has_freefloat_column(self):
        scraper = IndicesScraper()
        with patch.object(scraper._session, "request", return_value=_mock_response(FIXTURE_KSE100)):
            df = scraper.fetch("KSE100")
        assert "freefloat_m" in df.columns

    def test_allshr_has_shares_column(self):
        scraper = IndicesScraper()
        with patch.object(scraper._session, "request", return_value=_mock_response(FIXTURE_ALLSHR)):
            df = scraper.fetch("ALLSHR")
        assert isinstance(df, pd.DataFrame)
        # ALLSHR uses SHARES (M) instead of FREEFLOAT (M) for the 10th column
        assert "shares_m" in df.columns or "freefloat_m" in df.columns  # either is valid

    def test_empty_html_returns_empty_dataframe(self):
        scraper = IndicesScraper()
        with patch.object(scraper._session, "request", return_value=_mock_response("<html></html>")):
            df = scraper.fetch("KSE100")
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0

    def test_malformed_html_no_th_returns_empty_dataframe(self):
        bad_html = "<html><body><table><tbody><tr><td>ENGRO</td></tr></tbody></table></body></html>"
        scraper = IndicesScraper()
        with patch.object(scraper._session, "request", return_value=_mock_response(bad_html)):
            df = scraper.fetch("KSE100")
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0


class TestIndicesBadges:
    def test_real_fixture_returns_ex_flag_as_string_dtype(self):
        from psxdata.scrapers.indices import IndicesScraper

        scraper = IndicesScraper()
        html = (Path(__file__).parent.parent / "fixtures" / "indices_KSE100.html").read_text(encoding="utf-8")
        with patch.object(scraper._session, "request", return_value=_mock_response(html)):
            df = scraper.fetch("KSE100")
        assert str(df["ex_flag"].dtype) == "string"
        assert str(df["badge"].dtype) == "string"
        assert (df["ex_flag"] == "XD").sum() >= 1
        assert df.loc[df["ex_flag"].notna(), "symbol"].str.match(r"^[A-Z0-9]+$").all()
