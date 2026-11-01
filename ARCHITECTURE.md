# Architecture — psxdata

`psxdata` is a production-grade data pipeline with two consumer surfaces: a **Python library** (yfinance-style API) and a **FastAPI REST service**. It scrapes 8 PSX endpoints, normalizes and validates the data, caches it on disk, and exposes it through clean interfaces.

The hardest constraints are external: PSX is an unstable third-party dependency that changes HTML structure without notice and throttles aggressive scrapers. All endpoints are accessible via plain HTTP — some through hidden AJAX endpoints discovered during migration (see issue #31).

---

## Component Diagram

```mermaid
flowchart TD
    PSX["PSX Servers\ndps.psx.com.pk\n8 endpoints"]

    subgraph Scrapers["Scraper Layer"]
        BASE["BaseScraper\nsession · retry · rate limiter"]
        H["historical.py\nPOST · requests+BS4"]
        RT["realtime.py\nGET · requests+BS4"]
        SC["screener.py\nGET · requests+BS4"]
        IX["indices.py\nGET · requests+BS4"]
        SE["sectors.py\nGET · requests+BS4\n/sector-summary/sectorwise"]
        FU["fundamentals.py\nGET · requests+BS4\n/financial-reports-list"]
        DM["debt_market.py\nGET · requests+BS4"]
        ES["eligible_scrips.py\nGET · requests+BS4"]
    end

    subgraph Parsers["Parser Layer"]
        HTML["html.py\ndynamic header extraction"]
        NORM["normalizers.py\nmulti-format date parsing · type coerce"]
    end

    subgraph Validation["Validation + Models"]
        VAL["schemas.py (Pydantic v2)\nOHLC bounds · volume ≥ 0\ndate order · no duplicates"]
    end

    subgraph Cache["Cache Layer"]
        DISK["diskcache @ ~/.psxdata/cache/\nparquet format\nhistorical: never expires\ntoday: 15-min TTL"]
    end

    subgraph PublicAPI["Public Python API"]
        CLIENT["client.py\nstocks() · tickers() · indices()\nsectors() · fundamentals() · market.*"]
    end

    subgraph FastAPI["FastAPI Layer"]
        API["api/\nslowapi 60 req/min/IP\nRedis cache optional\nSwagger /docs · ReDoc /redoc"]
    end

    PSX -->|requests| BASE
    BASE --> H & RT & SC & IX & SE & FU & DM & ES
    H & RT & SC & IX & SE & FU & DM & ES -->|raw HTML / JSON| HTML
    HTML --> NORM
    NORM -->|typed DataFrames| VAL
    VAL -->|cache miss| DISK
    VAL -->|cache hit| CLIENT
    DISK --> CLIENT
    CLIENT --> FastAPI
```

---

## Data Flow

```
PSX Server → Scraper → Parser → Validator → Cache → Public Python API → FastAPI
```

On a cache hit, the path short-circuits after the Cache layer and never touches the Scraper.

---

## Directory Structure

```
psxdata/
├── psxdata/                    # Installable Python package (pip install psxdata)
│   ├── __init__.py             # Public API exports: stocks, tickers, indices, sectors, fundamentals, market
│   ├── client.py               # PSXClient — orchestrates scrapers, cache, validation
│   ├── constants.py            # All constants — no magic numbers anywhere in the codebase
│   ├── exceptions.py           # Custom exceptions: PSXUnavailableError, ParseError, ValidationError
│   ├── utils.py                # Date range chunking, rate limiter, shared helpers
│   ├── scrapers/
│   │   ├── base.py             # BaseScraper: session, retry, rate limit
│   │   ├── historical.py       # POST /historical — OHLCV data
│   │   ├── realtime.py         # GET /trading-board/{market}/{board} — live quotes
│   │   ├── indices.py          # GET /indices/{name} — index constituents
│   │   ├── sectors.py          # GET /sector-summary/sectorwise — sector aggregates
│   │   ├── fundamentals.py     # GET /financial-reports-list — P/E, EPS, book value
│   │   ├── screener.py         # GET /screener — all listed tickers
│   │   ├── debt_market.py      # GET /debt-market — TFCs, Sukuks
│   │   └── eligible_scrips.py  # GET /eligible-scrips — margin trading eligible stocks
│   ├── parsers/
│   │   ├── html.py             # Dynamic <th> header extraction, never fixed column positions
│   │   └── normalizers.py      # parse_date_safely(), type coercion, column name normalization
│   ├── cache/
│   │   └── disk_cache.py       # diskcache wrapper, parquet format, TTL logic
│   └── models/
│       └── schemas.py          # Pydantic v2 models for all data types
├── tests/
│   ├── unit/                   # Fast, no network — parsers, validators, cache, utils
│   ├── integration/            # Real PSX endpoints — marked @pytest.mark.integration
│   ├── fixtures/               # HTML snapshots from PSX endpoints (captured in Phase 0)
│   └── conftest.py             # Shared fixtures
├── docs/
│   └── PSX_ENDPOINTS.md        # Live endpoint verification results from Phase 0
├── .github/
│   ├── ISSUE_TEMPLATE/         # bug_report, feature_request, task, endpoint_change
│   ├── workflows/
│   │   ├── ci.yml              # lint + unit tests on every PR (Python 3.11, 3.12)
│   │   ├── integration.yml     # integration tests nightly + manual dispatch
│   │   └── publish.yml         # PyPI publish on tag v*
│   └── pull_request_template.md
├── ARCHITECTURE.md             # This file
├── CONTRIBUTING.md             # Setup, branch naming, PR process, issue-first policy
├── CODE_OF_CONDUCT.md          # Contributor Covenant v2.1
├── CHANGELOG.md                # Keep a Changelog format
├── SECURITY.md                 # Private vulnerability disclosure
├── LICENSE                     # MIT
└── pyproject.toml              # Package metadata, dependencies, tool config
```

---

## Scraper → Endpoint Map

| Scraper | PSX Endpoint | HTTP Method | Mode |
|---|---|---|---|
| `historical.py` | `/historical` | POST `{symbol}` | `requests` + BeautifulSoup |
| `realtime.py` | `/trading-board/{market}/{board}` | GET | `requests` + BeautifulSoup (AJAX) |
| `screener.py` | `/screener` | GET | `requests` + BeautifulSoup |
| `indices.py` | `/indices/{name}` | GET | `requests` + BeautifulSoup (AJAX) |
| `sectors.py` | `/sector-summary/sectorwise` | GET | `requests` + BeautifulSoup (AJAX) |
| `fundamentals.py` | `/financial-reports-list` | GET | `requests` + BeautifulSoup (AJAX) |
| `debt_market.py` | `/debt-market` | GET | `requests` + BeautifulSoup |
| `eligible_scrips.py` | `/eligible-scrips` | GET | `requests` + BeautifulSoup |
| — | `/symbols` | GET | JSON (instrument metadata) |

**Do NOT use:** `www.psx.com.pk/*` or `dps.psx.com.pk/timeseries/eod` — broken/redirect.

---

## Historical Data Fetching

`POST /historical {symbol}` returns **all** historical data for a symbol in one response — PSX ignores date params server-side. The scraper POSTs once and filters to `[start, end]` in memory. No chunking or concurrent fetching is needed.

---

## Key Components

### BaseScraper (`psxdata/scrapers/base.py`)

Every scraper inherits from `BaseScraper`. Provides:

- Persistent `requests.Session` with headers: `User-Agent`, `Accept`, `Accept-Language`, `Referer`, `X-Requested-With`
- Exponential backoff retry: 3 attempts, delays 1s / 2s / 4s
- Rate limiter: max 2 requests/second
- 30s timeout on every request
- `logging` at DEBUG level on every meaningful step

Playwright is retained for tooling only (endpoint discovery). Scrapers use `_get()` / `_post()` exclusively.

### Caching (`psxdata/cache/disk_cache.py`)

- Library: `diskcache`
- Location: `~/.psxdata/cache/`
- Format: parquet (fast, compressed, preserves dtypes)
- Cache key: `f"{symbol}_{start}_{end}"`
- Historical data: never expires
- Today's data: 15-minute TTL

### Parser Layer

- `html.py` — extracts `<th>` tags dynamically; never assumes fixed column count or position
- `normalizers.py` — multi-format date parsing with `dateutil` fuzzy fallback; type coercion

### FastAPI Layer

The REST API has moved to a standalone repository: [psxdata/psxdata-api](https://github.com/psxdata/psxdata-api). It consumes this library purely as a published PyPI dependency (`pip install psxdata`) and has no source-level coupling to this repo. See that repo's ARCHITECTURE notes for its design.

---

## Dependency Overview

```toml
# Core (always installed)
requests        # HTTP client for plain PSX endpoints
httpx           # Async HTTP (future use)
beautifulsoup4  # HTML table parsing
lxml            # BS4 parser backend
pandas          # DataFrame output format
python-dateutil # Fuzzy date parsing fallback
tqdm            # Progress bars for concurrent fetches
diskcache       # Disk-based cache
pydantic        # Data validation and models
playwright      # Dev/tooling only — endpoint discovery (not used by scrapers)

# api extra (pip install psxdata[api])
fastapi         # REST framework
uvicorn         # ASGI server
slowapi         # Rate limiting for FastAPI
redis           # API-level response cache (optional, falls back to in-memory)

# dev extra (pip install psxdata[dev])
pytest          # Test runner
pytest-cov      # Coverage reporting
pytest-asyncio  # Async test support
httpx           # FastAPI TestClient
ruff            # Linter
mypy            # Type checker
```

---

## Failure Modes & Mitigations

| Failure | Mitigation |
|---|---|
| PSX changes HTML structure | Dynamic `<th>` header extraction; log warning on unknown columns; open `endpoint_change` GitHub issue |
| PSX changes date format | Multi-format fallback + dateutil fuzzy parsing in `parse_date_safely()` |
| Network timeout / 5xx | 3-attempt exponential backoff (1s / 2s / 4s) in `BaseScraper._request()` |
| IP rate-limited by PSX | Max 2 req/sec global rate limiter; max 5 concurrent workers |
| PSX removes AJAX endpoint | Schema drift detected by `python tools/probe_endpoints.py --diff`; open `endpoint_change` issue |
| Redis unavailable | Silent fallback to in-memory cache + warning log |
| Corrupt / anomalous OHLC data | OHLC + volume + date validators; warn and keep partial rows; drop only if fully corrupt |

---

## Design Decisions & Trade-offs

**All endpoints via plain HTTP.** Every PSX JS-rendered page has hidden AJAX endpoints returning the same data. This was discovered during migration (see issue #31) and eliminates Playwright as a runtime dependency. Trade-off: if PSX removes AJAX endpoints, Playwright would need to return — `_playwright_page()` is retained for this scenario.

**ThreadPoolExecutor over asyncio.** Simpler error isolation per future; `requests` is synchronous. Trade-off: each worker holds an OS thread; fine at max 5, would need rethinking at 50+.

**diskcache + parquet, not a database.** Historical stock data is immutable once a date passes. Parquet is compact and fast for DataFrame round-trips. Trade-off: no query capability beyond key lookup — filtering happens in pandas post-load.

**Redis is optional.** API falls back to in-memory cache when Redis is unavailable. Frictionless local development. Trade-off: in-memory cache is per-process and dies on restart — adequate for dev, not for multi-worker production deployments.

**No auth on the public API.** PSX data is public; adding auth creates friction with no security benefit. Trade-off: fully open to abuse — mitigated by the 60 req/min rate limit per IP.

---

## What to Revisit as the System Grows

1. **AJAX endpoint stability.** PSX could remove or restructure AJAX endpoints at any time. The schema diff tool (`python tools/probe_endpoints.py --diff`) should be run on a schedule to detect drift early.
2. **Cache invalidation for today's data.** The 15-minute TTL is a proxy for "fresh enough." Explicit cache busting keyed to market open/close times would be more accurate.
3. **Corporate actions adjustment.** The `Adj_Close` formula depends on a PSX corporate actions feed whose reliability is unverified — highest-risk feature of Phase 3 API.
4. **Distributed rate limiter.** The 2 req/sec limiter is per-process. A multi-worker FastAPI deployment could exceed this by N×. A Redis-backed distributed rate limiter is needed at that scale.
5. **Column schema drift detection.** Currently unknown columns log a warning. A lightweight schema registry (even a JSON file) would let the system detect and alert on PSX endpoint changes automatically.
