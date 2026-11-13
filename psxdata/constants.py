"""All PSX endpoint URLs, timeouts, rate limits, cache config, and column mappings.

No magic numbers or hardcoded strings anywhere else in psxdata — import from here.
"""

# ---------------------------------------------------------------------------
# Network
# ---------------------------------------------------------------------------
BASE_URL = "https://dps.psx.com.pk"

ENDPOINTS: dict[str, str] = {
    # Page URLs
    "trading_panel": "/trading-panel",
    "debt_market": "/debt-market",
    "eligible_scrips": "/eligible-scrips",
    "screener": "/screener",
    # AJAX endpoints (discovered during migration — see issue #31)
    "historical": "/historical",
    "trading_board": "/trading-board",
    "symbols": "/symbols",
    "sector_summary": "/sector-summary/sectorwise",
    "financial_reports": "/financial-reports-list",
    "indices": "/indices",
}

# Single well-formed User-Agent — PSX showed no UA-based blocking in Phase 0.
# Add rotation here if PSX starts blocking (raise a GitHub issue first).
REQUEST_HEADERS: dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://dps.psx.com.pk/",
    "X-Requested-With": "XMLHttpRequest",
}

REQUEST_TIMEOUT: int = 30  # seconds

# ---------------------------------------------------------------------------
# Retry
# ---------------------------------------------------------------------------
MAX_RETRIES: int = 3
# Delays between attempts: len must equal MAX_RETRIES - 1
# (no sleep after the final attempt — we raise immediately)
RETRY_DELAYS: tuple[int, ...] = (1, 2)  # seconds between attempt 1→2 and 2→3

# Invariant — uses explicit raise, not assert (assert is stripped with python -O)
if len(RETRY_DELAYS) != MAX_RETRIES - 1:
    raise ValueError(
        f"constants.py misconfigured: len(RETRY_DELAYS)={len(RETRY_DELAYS)} "
        f"must equal MAX_RETRIES-1={MAX_RETRIES - 1}"
    )

# ---------------------------------------------------------------------------
# Rate limiting & concurrency
# ---------------------------------------------------------------------------
MAX_REQUESTS_PER_SECOND: int = 2
MAX_WORKERS: int = 5
DEFAULT_CHUNK_DAYS: int = 365

# ---------------------------------------------------------------------------
# Request token (X-Req-Id) - required on data endpoints since 2026-09-24 (#161)
# PSX embeds it in every HTML page as window.__ps._k; its JS sends it on XHRs.
# ---------------------------------------------------------------------------
TOKEN_PAGE: str = "/"  # HTML page that embeds window.__ps
TOKEN_HEADER: str = "X-Req-Id"
TOKEN_TTL: int = 240  # seconds - proactive refresh age (observed rotation ~5 min)
TOKEN_RETRY_BACKOFF: int = 60  # seconds before retrying after a failed token fetch

# ---------------------------------------------------------------------------
# Trading board structure
# ---------------------------------------------------------------------------
BOARDS: tuple[str, ...] = ("main", "gem", "bnb")
MARKETS: tuple[str, ...] = ("REG", "ODL", "DFC", "SQR", "CSF")

# Badges PSX shows next to a ticker that mark a corporate action:
# XD ex-dividend, XB ex-bonus, XR ex-rights. Others (e.g. NC) are not.
EX_FLAGS: frozenset[str] = frozenset({"XD", "XB", "XR"})

INDEX_NAMES: tuple[str, ...] = (
    "KSE100", "KSE100PR", "ALLSHR", "KSE30", "KMI30", "BKTI", "OGTI",
    "KMIALLSHR", "PSXDIV20", "UPP9", "NITPGI", "NBPPGI", "MZNPI",
    "JSMFI", "ACI", "JSGBKTI", "HBLTTI", "MII30",
)

# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------
CACHE_DIR: str = "~/.psxdata/cache/"
CACHE_TTL_TODAY: int = 900  # 15 minutes in seconds

# screener() traded_today: if fewer symbols than this have volume on the REG
# main board, the board is treated as not yet populated (pre-open, early
# session) and the flag is <NA>. A full session has ~450-500.
TRADED_TODAY_MIN_SYMBOLS: int = 100

# ---------------------------------------------------------------------------
# Column name mapping
# Raw PSX <th> header text -> internal snake_case name.
# Unknown headers fall back to normalize_column_name() + logged warning.
# ---------------------------------------------------------------------------
COLUMN_MAP: dict[str, str] = {
    "DATE": "date",
    "OPEN": "open",
    "HIGH": "high",
    "LOW": "low",
    "CLOSE": "close",
    "VOLUME": "volume",
    "CHANGE (%)": "change_pct",
    "CHANGE": "change",
    "% Change": "change_pct",
    "SYMBOL": "symbol",
    "NAME": "name",
    "Symbol": "symbol",
    "Name": "name",
    "SECTOR": "sector",
    "LISTED IN": "listed_in",
    "MARKET CAP.": "market_cap",
    "MARKET CAP. (B)": "market_cap_b",
    "PRICE": "price",
    "PE RATIO (TTM)": "pe_ratio",
    "DIVIDEND YIELD (%)": "dividend_yield",
    "FREE FLOAT": "free_float",
    "30D VOLUME AVG.": "volume_avg_30d",
    "1-YEAR CH. (%) *": "change_1y_pct",
    "LDCP": "ldcp",
    "CURRENT": "current",
    "Current": "current",
    "ADVANCE": "advance",
    "DECLINE": "decline",
    "UNCHANGE": "unchanged",
    "TURNOVER": "turnover",
    "SECTOR CODE": "sector_code",
    "Sector Code": "sector_code",
    "SECTOR NAME": "sector_name",
    "Sector Name": "sector_name",
    "Index": "index_name",
    "High": "high",
    "Low": "low",
    "YEAR": "year",
    "TYPE": "type",
    "PERIOD ENDED": "period_ended",
    "POSTING DATE": "posting_date",
    "POSTING TIME": "posting_time",
    "DOCUMENT": "document",
    "Security Code": "security_code",
    "Security Name": "security_name",
    "Face Value": "face_value",
    "Listing Date": "listing_date",
    "Issue Date": "issue_date",
    "Issue Size": "issue_size",
    "Maturity Date": "maturity_date",
    "Coupon/Rental Rate": "coupon_rate",
    "Previous Coupon/Rental Date": "prev_coupon_date",
    "Next Coupon/Rental Date": "next_coupon_date",
    "Outstanding Days": "outstanding_days",
    "Remaining Years": "remaining_years",
    "Advance": "advance",
    "Decline": "decline",
    "Unchange": "unchanged",
    "Turnover": "turnover",
    "Market Cap. (B)": "market_cap_b",
    # Trading board columns
    "BID VOL.": "bid_vol",
    "BID PRICE": "bid_price",
    "OFFER VOL.": "offer_vol",
    "OFFER PRICE": "offer_price",
    # BNB-specific (debt trading board)
    "BID YIELD (%)": "bid_yield",
    "OFFER YIELD (%)": "offer_yield",
    "LTP": "ltp",
    "LTY (%)": "lty",
    "LDCY (%)": "ldcy",
    # Index constituents
    "Current Index": "current_index",
    "IDX WTG (%)": "idx_weight",
    "IDX POINT": "idx_point",
    "FREEFLOAT (M)": "freefloat_m",
    "SHARES (M)": "shares_m",
    "MARKET CAP (M)": "market_cap_m",
}
