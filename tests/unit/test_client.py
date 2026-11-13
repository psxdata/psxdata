"""Unit tests for psxdata/client.py — all mocked, no network required."""
from __future__ import annotations

from unittest.mock import MagicMock

import pandas as pd
import pytest

from unittest.mock import patch

from psxdata.client import PSXClient

# Fixed "today" used throughout — avoids flakiness around midnight.
FIXED_TODAY = pd.Timestamp("2024-06-15")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def freeze_today(monkeypatch):
    """Patch psxdata.client._today() to return FIXED_TODAY for all tests."""
    monkeypatch.setattr("psxdata.client._today", lambda: FIXED_TODAY)


@pytest.fixture
def client(tmp_path):
    """PSXClient with a real isolated DiskCache and all scrapers replaced by MagicMocks."""
    c = PSXClient(cache_dir=str(tmp_path / "cache"))
    c._historical = MagicMock()
    c._screener = MagicMock()
    c._realtime = MagicMock()
    # Default: empty boards, so traded_today is unknown. Tests that care set their own.
    c._realtime.fetch.return_value = pd.DataFrame()
    c._symbols = MagicMock()
    c._indices = MagicMock()
    c._sectors = MagicMock()
    c._fundamentals = MagicMock()
    c._debt_market = MagicMock()
    c._eligible_scrips = MagicMock()
    return c


@pytest.fixture
def today():
    return FIXED_TODAY


@pytest.fixture
def ohlcv_df(today):
    """Sample OHLCV DataFrame spanning yesterday and today."""
    yesterday = today - pd.Timedelta(days=1)
    return pd.DataFrame({
        "date": [yesterday, today],
        "open": [100.0, 101.0],
        "high": [105.0, 106.0],
        "low": [98.0, 99.0],
        "close": [103.0, 104.0],
        "volume": pd.array([10000, 11000], dtype="Int64"),
        "is_anomaly": [False, False],
    })


@pytest.fixture
def hist_only_df(today):
    """Sample OHLCV DataFrame with only historical rows (all dates before today)."""
    day_before = today - pd.Timedelta(days=2)
    yesterday = today - pd.Timedelta(days=1)
    return pd.DataFrame({
        "date": [day_before, yesterday],
        "open": [100.0, 101.0],
        "high": [105.0, 106.0],
        "low": [98.0, 99.0],
        "close": [103.0, 104.0],
        "volume": pd.array([10000, 11000], dtype="Int64"),
        "is_anomaly": [False, False],
    })


@pytest.fixture
def screener_df():
    return pd.DataFrame({
        "symbol": ["ENGRO", "LUCK", "HBL"],
        "price": [250.0, 150.0, 100.0],
        "market_cap": [1e9, 5e8, 8e8],
    })


@pytest.fixture
def symbols_df():
    return pd.DataFrame({
        "symbol": ["ENGRO", "LUCK", "HBL"],
        "name": ["Engro Corp", "Lucky Cement", "HBL"],
        "sector_name": ["Fertilizer", "Cement", "Banks"],
    })


@pytest.fixture
def indices_df():
    return pd.DataFrame({
        "symbol": ["ENGRO", "LUCK"],
        "current_index": [45000.0, 45100.0],
        "idx_weight": [2.5, 1.8],
    })


@pytest.fixture
def sectors_df():
    return pd.DataFrame({
        "sector_code": [1, 2],
        "sector_name": ["Fertilizer", "Cement"],
        "advance": [5, 3],
        "decline": [2, 4],
        "unchanged": [1, 1],
        "turnover": [1e8, 5e7],
        "market_cap_b": [50.0, 30.0],
    })


@pytest.fixture
def fundamentals_df():
    return pd.DataFrame({
        "symbol": ["ENGRO", "ENGRO", "LUCK"],
        "year": [2024, 2023, 2024],
        "type": ["Annual", "Annual", "Annual"],
        "period_ended": pd.to_datetime(["2024-12-31", "2023-12-31", "2024-12-31"]),
        "posting_date": pd.to_datetime(["2025-02-15", "2024-02-10", "2025-02-20"]),
    })


# ---------------------------------------------------------------------------
# stocks()
# ---------------------------------------------------------------------------

class TestStocks:
    def test_stocks_cache_miss_fetches_scraper(self, client, ohlcv_df):
        """On cache miss the scraper is called and the result is returned."""
        client._historical.fetch.return_value = ohlcv_df
        result = client.stocks("ENGRO", cache=True)
        client._historical.fetch.assert_called_once_with("ENGRO", start=None, end=None)
        assert not result.empty

    def test_stocks_cache_hit_skips_scraper(self, client, hist_only_df, today):
        """When historical data is cached and today is not needed, scraper is not called."""
        yesterday = today - pd.Timedelta(days=1)
        client._cache.set("ENGRO_historical", hist_only_df, ttl=None)
        result = client.stocks("ENGRO", end=yesterday.date(), cache=True)
        client._historical.fetch.assert_not_called()
        assert len(result) == len(hist_only_df)

    def test_stocks_today_split_cached_separately(self, client, ohlcv_df, today):
        """After a cache miss, historical and today rows are stored under separate keys."""
        client._historical.fetch.return_value = ohlcv_df
        client.stocks("ENGRO", cache=True)
        hist_cached = client._cache.get("ENGRO_historical")
        today_cached = client._cache.get("ENGRO_today")
        assert hist_cached is not None, "historical rows should be cached"
        assert today_cached is not None, "today rows should be cached"
        assert (hist_cached["date"] < today).all()
        assert (today_cached["date"] >= today).all()

    def test_stocks_day_boundary_today_cache_covers_past_end(self, client, today):
        """After day rollover, yesterday's row in {sym}_today is returned for end=yesterday.

        Regression: before the fix, need_today=False caused {sym}_today to be skipped
        entirely, so the most recent historical row (not yet moved to {sym}_historical)
        was silently omitted.
        """
        yesterday = today - pd.Timedelta(days=1)
        day_before = today - pd.Timedelta(days=2)

        # Simulate post-rollover state: historical only has data up to day_before;
        # yesterday's row is still in the today cache (not yet expired).
        hist_df = pd.DataFrame({
            "date": [day_before],
            "open": [100.0], "high": [105.0], "low": [98.0], "close": [103.0],
            "volume": pd.array([10000], dtype="Int64"), "is_anomaly": [False],
        })
        today_df = pd.DataFrame({
            "date": [yesterday],
            "open": [101.0], "high": [106.0], "low": [99.0], "close": [104.0],
            "volume": pd.array([11000], dtype="Int64"), "is_anomaly": [False],
        })
        client._cache.set("ENGRO_historical", hist_df, ttl=None)
        client._cache.set("ENGRO_today", today_df, ttl=900)

        result = client.stocks("ENGRO", end=yesterday.date(), cache=True)

        client._historical.fetch.assert_not_called()
        assert len(result) == 2
        assert yesterday in result["date"].values

    def test_stocks_cache_false_bypasses_cache(self, client, ohlcv_df):
        """cache=False always calls the scraper regardless of what is in cache."""
        client._historical.fetch.return_value = ohlcv_df
        client.stocks("ENGRO", cache=True)   # populates cache
        client.stocks("ENGRO", cache=False)  # must bypass and call again
        assert client._historical.fetch.call_count == 2

    def test_stocks_invalid_range_raises(self, client):
        """start > end raises ValueError before any scraper call."""
        with pytest.raises(ValueError, match="must not be after"):
            client.stocks("ENGRO", start="2024-12-31", end="2024-01-01")
        client._historical.fetch.assert_not_called()

    def test_stocks_empty_response(self, client):
        """Scraper returning empty DataFrame is forwarded unchanged."""
        empty = pd.DataFrame(
            columns=["date", "open", "high", "low", "close", "volume", "is_anomaly"]
        )
        client._historical.fetch.return_value = empty
        result = client.stocks("ENGRO", cache=False)
        assert result.empty
        assert list(result.columns) == [
            "date", "open", "high", "low", "close", "volume", "is_anomaly"
        ]


# ---------------------------------------------------------------------------
# quote()
# ---------------------------------------------------------------------------

class TestQuote:
    def test_quote_returns_matching_row(self, client, screener_df):
        """quote() returns the single row matching the requested symbol."""
        client._screener.fetch.return_value = screener_df
        result = client.quote("ENGRO", cache=False)
        assert len(result) == 1
        assert result["symbol"].iloc[0] == "ENGRO"

    def test_quote_unknown_symbol_returns_empty(self, client, screener_df):
        """Symbol absent from the screener returns an empty DataFrame."""
        client._screener.fetch.return_value = screener_df
        result = client.quote("XXXX", cache=False)
        assert result.empty

    def test_quote_caches_screener(self, client, screener_df):
        """Screener is fetched once; subsequent calls for different symbols reuse it."""
        client._screener.fetch.return_value = screener_df
        client._realtime.fetch.side_effect = _boards(_main(["ENGRO"]))
        client.quote("ENGRO", cache=True)
        client.quote("LUCK", cache=True)
        client._screener.fetch.assert_called_once()


# ---------------------------------------------------------------------------
# tickers()
# ---------------------------------------------------------------------------

class TestTickers:
    def test_tickers_no_index(self, client, symbols_df):
        """tickers() with no index returns all symbol strings from SymbolsScraper."""
        client._symbols.fetch.return_value = symbols_df
        result = client.tickers(cache=False)
        client._symbols.fetch.assert_called_once()
        assert result == ["ENGRO", "LUCK", "HBL"]
        assert isinstance(result, list)
        assert all(isinstance(s, str) for s in result)

    def test_tickers_with_index(self, client, indices_df):
        """tickers(index=...) uses IndicesScraper and extracts the symbol column."""
        client._indices.fetch.return_value = indices_df
        result = client.tickers(index="KSE100", cache=False)
        client._indices.fetch.assert_called_once_with("KSE100")
        assert result == ["ENGRO", "LUCK"]

    def test_tickers_empty_result(self, client):
        """Scraper returning empty DataFrame yields an empty list."""
        client._symbols.fetch.return_value = pd.DataFrame()
        result = client.tickers(cache=False)
        assert result == []


# ---------------------------------------------------------------------------
# indices()
# ---------------------------------------------------------------------------

class TestIndices:
    def test_indices_returns_dataframe(self, client, indices_df):
        """indices() returns the full constituent DataFrame from IndicesScraper."""
        client._indices.fetch.return_value = indices_df
        result = client.indices("KSE100", cache=False)
        client._indices.fetch.assert_called_once_with("KSE100")
        pd.testing.assert_frame_equal(result, indices_df)


# ---------------------------------------------------------------------------
# sectors()
# ---------------------------------------------------------------------------

class TestSectors:
    def test_sectors_returns_dataframe(self, client, sectors_df):
        """sectors() returns the full sector summary DataFrame."""
        client._sectors.fetch.return_value = sectors_df
        result = client.sectors(cache=False)
        client._sectors.fetch.assert_called_once()
        pd.testing.assert_frame_equal(result, sectors_df)


# ---------------------------------------------------------------------------
# fundamentals()
# ---------------------------------------------------------------------------

from psxdata.constants import TRADED_TODAY_MIN_SYMBOLS  # noqa: E402

# Filler symbols so the main board looks like a populated session.
_FILLER = [f"X{i:03d}" for i in range(TRADED_TODAY_MIN_SYMBOLS)]


def _board(symbols, volumes=None):
    volumes = volumes if volumes is not None else [1000] * len(symbols)
    return pd.DataFrame({"symbol": symbols, "volume": volumes})


def _main(symbols=(), volumes=None):
    """A populated REG main board: the given symbols plus enough filler."""
    symbols = list(symbols)
    volumes = list(volumes) if volumes is not None else [1000] * len(symbols)
    return _board(symbols + _FILLER, volumes + [1000] * len(_FILLER))


def _boards(main, gem=None):
    """side_effect for RealtimeScraper.fetch(market, board)."""
    tables = {("REG", "main"): main, ("REG", "gem"): gem if gem is not None else pd.DataFrame()}

    def fetch(market, board):
        table = tables[(market, board)]
        if isinstance(table, Exception):
            raise table
        return table

    return fetch


def _flags(client):
    return client.screener(cache=False).set_index("symbol")["traded_today"]


class TestScreener:
    def test_screener_returns_all_rows_unfiltered(self, client, screener_df):
        """screener() returns every screener row, with traded_today added."""
        client._screener.fetch.return_value = screener_df
        client._realtime.fetch.side_effect = _boards(_main(["ENGRO", "LUCK", "HBL"]))
        result = client.screener(cache=False)
        client._screener.fetch.assert_called_once()
        pd.testing.assert_frame_equal(result.drop(columns="traded_today"), screener_df)

    def test_screener_shares_cache_with_quote(self, client, screener_df):
        """screener() and quote() share one cached snapshot."""
        client._screener.fetch.return_value = screener_df
        client._realtime.fetch.side_effect = _boards(_main(["ENGRO"]))
        client.quote("ENGRO", cache=True)
        result = client.screener(cache=True)
        client._screener.fetch.assert_called_once()
        assert client._realtime.fetch.call_count == 2  # REG main + REG gem, once
        assert str(result["traded_today"].dtype) == "boolean"  # survives the cache
        assert bool(result.set_index("symbol").loc["ENGRO", "traded_today"]) is True

    def test_traded_today_marks_symbols_on_the_boards(self, client, screener_df):
        """traded_today: volume > 0 on REG main or REG gem."""
        client._screener.fetch.return_value = screener_df
        client._realtime.fetch.side_effect = _boards(
            main=_main(["ENGRO", "LUCK"], [5000, 0]),
            gem=_board(["HBL"]),
        )
        result = _flags(client)
        assert result.to_dict() == {"ENGRO": True, "LUCK": False, "HBL": True}
        assert str(result.dtype) == "boolean"

    def test_traded_today_false_for_delisted_ghost_row(self, client):
        """PSX keeps delisted names (e.g. FFBL) in the screener with their
        last-day move; they never appear on the board."""
        client._screener.fetch.return_value = pd.DataFrame(
            {"symbol": ["FFBL", "FFC"], "price": [88.94, 400.0], "change_pct": [8.07, 0.5]}
        )
        client._realtime.fetch.side_effect = _boards(_main(["FFC"]))
        assert _flags(client).to_dict() == {"FFBL": False, "FFC": True}

    def test_nan_and_text_volume_count_as_no_trade(self, client, screener_df):
        client._screener.fetch.return_value = screener_df
        client._realtime.fetch.side_effect = _boards(
            _main(["ENGRO", "LUCK", "HBL"], [float("nan"), "-", "abc"])
        )
        assert _flags(client).to_dict() == {"ENGRO": False, "LUCK": False, "HBL": False}

    def test_unknown_when_boards_empty(self, client, screener_df):
        """An empty board (e.g. before PSX publishes the session) is not
        evidence that nothing traded: the flag is <NA>, not False."""
        client._screener.fetch.return_value = screener_df
        result = client.screener(cache=False)
        assert result["traded_today"].isna().all()
        assert str(result["traded_today"].dtype) == "boolean"

    def test_unknown_when_main_empty_even_if_gem_has_rows(self, client, screener_df):
        client._screener.fetch.return_value = screener_df
        client._realtime.fetch.side_effect = _boards(main=pd.DataFrame(), gem=_board(["HBL"]))
        assert _flags(client).isna().all()

    def test_unknown_when_main_board_part_populated(self, client, screener_df, caplog):
        """Fewer than TRADED_TODAY_MIN_SYMBOLS traded: treat as not yet populated."""
        client._screener.fetch.return_value = screener_df
        client._realtime.fetch.side_effect = _boards(_board(["ENGRO", "LUCK"]))
        with caplog.at_level("WARNING"):
            assert _flags(client).isna().all()
        assert "only 2 traded symbols" in caplog.text

    def test_unknown_when_main_board_has_no_volume_column(self, client, screener_df):
        client._screener.fetch.return_value = screener_df
        client._realtime.fetch.side_effect = _boards(pd.DataFrame({"symbol": _FILLER}))
        assert _flags(client).isna().all()

    @pytest.mark.parametrize("exc", ["psx", "other"])
    def test_unknown_when_main_board_fetch_fails(self, client, screener_df, caplog, exc):
        """No board error, PSX or otherwise, fails screener(); the flag is <NA>."""
        from psxdata.exceptions import PSXConnectionError

        client._screener.fetch.return_value = screener_df
        err = PSXConnectionError("boom") if exc == "psx" else ValueError("schema changed")
        client._realtime.fetch.side_effect = _boards(main=err)
        with caplog.at_level("WARNING"):
            result = client.screener(cache=False)
        assert len(result) == 3
        assert result["traded_today"].isna().all()
        assert "REG main trading board" in caplog.text

    def test_gem_failure_keeps_main_traders(self, client, screener_df):
        """If only GEM fails, main-board traders are True and the rest unknown."""
        client._screener.fetch.return_value = screener_df
        client._realtime.fetch.side_effect = _boards(
            main=_main(["ENGRO"]), gem=RuntimeError("gem down")
        )
        result = _flags(client)
        assert bool(result["ENGRO"]) is True
        assert result[["LUCK", "HBL"]].isna().all()

    def test_unknown_flag_is_not_cached(self, client, screener_df):
        """A board blip shouldn't stick for the cache TTL."""
        client._screener.fetch.return_value = screener_df
        client.screener(cache=True)  # boards empty -> <NA>
        client._realtime.fetch.side_effect = _boards(_main(["ENGRO"]))
        result = client.screener(cache=True)
        assert client._screener.fetch.call_count == 2
        assert bool(result.set_index("symbol").loc["ENGRO", "traded_today"]) is True

    def test_quote_includes_traded_today(self, client, screener_df):
        client._screener.fetch.return_value = screener_df
        client._realtime.fetch.side_effect = _boards(_main(["LUCK"]))
        assert bool(client.quote("LUCK", cache=False)["traded_today"].iloc[0]) is True

    def test_empty_screener_skips_board_fetch(self, client):
        client._screener.fetch.return_value = pd.DataFrame()
        assert client.screener(cache=False).empty
        client._realtime.fetch.assert_not_called()


class TestFundamentals:
    def test_fundamentals_no_filter(self, client, fundamentals_df):
        """fundamentals() with no symbol returns all rows."""
        client._fundamentals.fetch.return_value = fundamentals_df
        result = client.fundamentals(cache=False)
        assert len(result) == len(fundamentals_df)

    def test_fundamentals_symbol_filter(self, client, fundamentals_df):
        """fundamentals(symbol=...) filters rows in memory by symbol."""
        client._fundamentals.fetch.return_value = fundamentals_df
        result = client.fundamentals(symbol="ENGRO", cache=False)
        assert len(result) == 2
        assert (result["symbol"] == "ENGRO").all()


# ---------------------------------------------------------------------------
# debt_market()
# ---------------------------------------------------------------------------

class TestDebtMarket:
    @pytest.fixture
    def mock_tables(self):
        return {
            "table_0": pd.DataFrame({"security_name": ["Bond A"]}),
            "table_1": pd.DataFrame({"security_name": ["Bond B"]}),
        }

    def test_debt_market_returns_dict(self, client, mock_tables):
        """On cache miss the scraper is called and the result is returned."""
        client._debt_market.fetch.return_value = mock_tables
        result = client.debt_market(cache=True)
        client._debt_market.fetch.assert_called_once()
        assert set(result.keys()) == {"table_0", "table_1"}

    def test_debt_market_cache_hit_skips_scraper(self, client, mock_tables):
        """Second call with cache=True reuses cached result without fetching."""
        client._debt_market.fetch.return_value = mock_tables
        client.debt_market(cache=True)
        client.debt_market(cache=True)
        client._debt_market.fetch.assert_called_once()

    def test_debt_market_cache_false_bypasses(self, client, mock_tables):
        """cache=False always calls the scraper regardless of cache state."""
        client._debt_market.fetch.return_value = mock_tables
        client.debt_market(cache=True)
        client.debt_market(cache=False)
        assert client._debt_market.fetch.call_count == 2


# ---------------------------------------------------------------------------
# eligible_scrips()
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# mock_cache fixture (shared by symbols tests)
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_cache(tmp_path):
    """Return a PSXClient wired to an isolated real DiskCache."""
    c = PSXClient(cache_dir=str(tmp_path / "cache"))
    return c


# ---------------------------------------------------------------------------
# symbols()
# ---------------------------------------------------------------------------

def test_symbols_returns_dataframe(mock_cache):
    """symbols() returns the full DataFrame from SymbolsScraper."""
    expected = pd.DataFrame({
        "symbol": ["ENGRO", "LUCK"],
        "name": ["Engro Corporation", "Lucky Cement"],
        "sector_name": ["FERTILIZER", "CEMENT"],
        "is_etf": [False, False],
        "is_debt": [False, False],
        "is_gem": [False, False],
    })
    client = mock_cache
    with patch.object(client._symbols, "fetch", return_value=expected):
        result = client.symbols(cache=False)
    assert list(result["symbol"]) == ["ENGRO", "LUCK"]
    assert "sector_name" in result.columns


def test_symbols_shares_cache_with_tickers(mock_cache):
    """symbols() and tickers(index=None) share the 'symbols_all' cache key."""
    symbols_df = pd.DataFrame({
        "symbol": ["ENGRO"],
        "name": ["Engro Corporation"],
        "sector_name": ["FERTILIZER"],
        "is_etf": [False],
        "is_debt": [False],
        "is_gem": [False],
    })
    client = mock_cache
    with patch.object(client._symbols, "fetch", return_value=symbols_df) as mock_fetch:
        client.tickers()   # populates symbols_all cache
        client.symbols()   # should reuse cache, not call fetch again
    mock_fetch.assert_called_once()


class TestEligibleScrips:
    @pytest.fixture
    def mock_tables(self):
        return {
            f"table_{i}": pd.DataFrame({"symbol": [f"SYM{i}"]})
            for i in range(9)
        }

    def test_eligible_scrips_returns_dict(self, client, mock_tables):
        """On cache miss the scraper is called and the result is returned."""
        client._eligible_scrips.fetch.return_value = mock_tables
        result = client.eligible_scrips(cache=True)
        client._eligible_scrips.fetch.assert_called_once()
        assert set(result.keys()) == {f"table_{i}" for i in range(9)}

    def test_eligible_scrips_cache_hit_skips_scraper(self, client, mock_tables):
        """Second call with cache=True reuses cached result without fetching."""
        client._eligible_scrips.fetch.return_value = mock_tables
        client.eligible_scrips(cache=True)
        client.eligible_scrips(cache=True)
        client._eligible_scrips.fetch.assert_called_once()

    def test_eligible_scrips_cache_false_bypasses(self, client, mock_tables):
        """cache=False always calls the scraper regardless of cache state."""
        client._eligible_scrips.fetch.return_value = mock_tables
        client.eligible_scrips(cache=True)
        client.eligible_scrips(cache=False)
        assert client._eligible_scrips.fetch.call_count == 2
