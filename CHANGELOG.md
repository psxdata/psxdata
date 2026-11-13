# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added

- `badge` and `ex_flag` on `screener()`/`quote()`, `indices()` and the trading boards (pandas `string` dtype, `<NA>` when empty). PSX shows a badge next to some tickers. `badge` is its text (`XD`, `XB`, `XR`, and others such as `NC` or `WU`; several are joined with `+`). `ex_flag` keeps only the corporate-action ones: XD ex-dividend, XB ex-bonus, XR ex-rights, plus any other `X` code, which is also logged. Since 1.2.1 the badge was dropped to keep tickers clean; now it's kept beside them, which lets you attribute a price drop to a stock going ex (on 2026-11-13, 19 KSE-100 constituents were XD). Cached screener and index data from older versions is refetched.

---

## [1.4.0] - 2026-11-13

### Added

- `screener()` and `quote()` now include `sector_code` and `sector_name`. PSX's screener gives only a sector code, which the scraper parses as a number (`sector` = 809.0). `sector_code` is the code as PSX writes it (`"0809"`) and `sector_name` its name from `sectors()` (`"FERTILIZER"`). Both are `<NA>` when PSX gives no sector; `sector_name` is `<NA>` if the sector list can't be read; that never fails `screener()`. A snapshot cached by 1.3.0, which lacks these columns, is refetched. `sector` is unchanged. A screener fetch now also reads the sector list (cached the same way as `sectors()`).

### Changed

- `screener()` and `quote()` return `pe_ratio` as NaN where PSX shows 0.00. PSX uses 0.00 when there is no meaningful P/E (e.g. loss-making companies; 393 of 755 symbols on 2026-11-13, never negative), and a 0 sorted those as the cheapest stocks. If you relied on `pe_ratio == 0`, use `pe_ratio.isna()`. `dividend_yield` 0 is unchanged; it means no dividend.

---

## [1.3.0] - 2026-11-13

### Added

- `screener()` and `quote()` now include `traded_today`, a nullable boolean. PSX keeps some symbols in its screener after they stop trading, including delisted ones such as FFBL and ENGRO, and shows their last trading day's price and `change_pct` as if current. `traded_today` is `True` when the symbol has volume on the regular-market main or GEM trading board so far in the session, `False` when it doesn't, and `<NA>` when the board can't be read, is empty, or has fewer than 100 traded symbols (not yet populated). Filter on it before ranking daily moves. `False` never means delisted; during the session it only means "no trade yet". A board failure never fails `screener()`, and a result with an unknown flag isn't cached. Each screener fetch now makes two extra requests (REG main and GEM boards), so a slow or failing board adds latency to `screener()` and `quote()` on a cache miss.

---

## [1.2.1] - 2026-11-01

### Fixed

- Screener `market_cap` and `free_float` were NULL for every symbol. PSX shows abbreviated text ("167.7B", "7.0M") in those cells and keeps the exact value in the `data-order` attribute; the HTML table parser now uses it for abbreviated numbers. Applies to every table parsed through `parse_html_table`.
- Symbols with PSX's ex-dividend badge (`XD`) were returned with the badge glued on (`BAHL` came back as `BAHLXD`), so they looked missing from the screener and renamed in index constituents. Symbol cells now use the exact `data-order` value.

## [1.2.0] - 2026-09-30

### Added

- Proxy support (#162). `PSXClient(proxy=...)` and the new `psxdata.configure(proxy=...)` (for the module-level functions) route every PSX request through a proxy you choose, including the `X-Req-Id` token fetch, so the token and the data requests come from the same egress IP. Accepts a single URL (`http://`, `https://`, `socks5://`, optionally with `user:pass@`) or a `requests`-style per-scheme dict. An explicit proxy takes precedence over `HTTP_PROXY`/`HTTPS_PROXY`. Without one, behaviour is unchanged and those environment variables still apply. Proxy credentials are redacted from all log lines and error messages. A proxy connection failure raises `PSXConnectionError` naming the (redacted) proxy. `BaseScraper` and `TokenProvider` gain an optional `proxy`/`proxies` argument.
- `psxdata[socks]` optional extra (`requests[socks]`) for SOCKS proxies. Passing a SOCKS URL without it raises an `ImportError` explaining how to install it.

---

## [1.1.1] - 2026-09-25

### Fixed

- All PSX data requests failing with `PSXAuthError` (403) since 2026-09-24. PSX now requires an `X-Req-Id` request token (published in every page as `window.__ps._k`) on its data endpoints. psxdata now fetches this token automatically, shares it across all scrapers in the process, refreshes it every 4 minutes, and on a 403 refreshes it and retries the request once before raising `PSXAuthError`. If no token can be obtained, requests are sent without it and a warning is logged. No API changes (#161).

---

## [1.1.0] - 2026-09-02

### Added

- `PSXClient.screener()` and top-level `psxdata.screener()` — return the full, unfiltered PSX screener table (all ~729 symbols, all columns). Shares the `"screener_all"` cache key with `quote()`, so calling both never results in a double fetch.

## [1.0.0] - 2026-08-31

First stable release. The public API (`PSXClient`, `stocks`, `tickers`, `quote`, `indices`, `sectors`, `fundamentals`, `debt_market`, `eligible_scrips`, `symbols`) has been stable since `0.1.0a1` with no breaking changes across five alpha releases and real-world use — from here, breaking changes will be reserved for major version bumps per [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

### Added

- `README.md`: Data Availability section clarifying that only daily historical OHLCV and live quote snapshots are supported, since PSX does not expose a historical intraday data feed.
- `README.md`: PyPI downloads badge.

### Fixed

- `tools/probe_endpoints.py`: `diff_schemas()` no longer fails the schema-drift CI check on row-count-only changes for live order-book boards (`trading_board_reg_gem`, `trading_board_bnb_bnb`), whose row counts swing with market activity rather than API schema drift. Row-count swings are now reported separately as informational notes; column, status, and endpoint-presence drift still fail the check.

### Changed

- Removed the automated Claude Code Review GitHub Actions workflow.
- Bumped `actions/setup-python` from 6 to 7 in CI workflows.

---

## [0.1.0a5] - 2026-07-03

### Fixed

- `psxdata/scrapers/screener.py`: `change_pct` was missing from the `numeric_cols` coercion tuple, leaving it as a raw percent string (e.g. `"1.24%"`) instead of a float. This broke every `GET /stocks/{symbol}/quote` call in the `psxdata-api` service, whose `QuoteData` schema requires `change_pct: float | None` — confirmed failing in production. Added `"change_pct"` to `numeric_cols` and a regression test asserting the column is numeric after `ScreenerScraper.fetch()`.

---

## [0.1.0a4] - 2026-07-03

### Changed

- Extracted the FastAPI REST layer (`api/`) into a standalone repository, [psxdata/psxdata-api](https://github.com/psxdata/psxdata-api), with full git history preserved via `git filter-repo`. The API now ships and versions independently of this library.

### Added

- Phase 4: Added multi-stage `Dockerfile` for the `api/` service — `builder` stage installs dependencies into a venv, `runtime` stage copies only the venv and `api/` source, resulting in a minimal image with no build tools.
- Phase 4: Added `.dockerignore` — strips all non-essential paths (`psxdata/`, `tests/`, `docs/`, `tools/`, `examples/`, build artifacts, config files) from the Docker build context.
- Phase 4: `Dockerfile` runs as non-root user `psxuser` with a pre-created `~/.psxdata/cache/` directory for psxdata's disk cache.
- Phase 4: `Dockerfile` supports a configurable `PORT` environment variable (default `8000`) via shell-form `CMD exec uvicorn ...` for correct signal handling.
- Phase 4: Added `HEALTHCHECK` (`GET /health`, 30s interval, 60s start period, 5 retries) to the `Dockerfile`.
- Phase 4: Added `.github/workflows/docker-publish.yml` — builds and pushes the `api/` Docker image to Docker Hub (`mtauha/psxdata-api`) as `latest` and the tag's version on every `v*` tag push, using `docker/login-action`, `docker/setup-buildx-action`, and `docker/build-push-action` with GitHub Actions layer caching.

- Phase 4: Added `CONTRIBUTING.md` guide for adding new API endpoints — router pattern, registry wiring, response envelope, typed `response_model`, error codes, `Depends()` injection, and `TestClient` fixture conventions.
- Phase 4: Added `test-api` CI job that installs `.[dev,api]` and runs `tests/unit/api/` in isolation from the core test environment.
- Phase 4: Added `api/schemas.py` — six Pydantic v2 models (`MetaSingle`, `MetaList`, `ErrorDetail`, `ErrorEnvelope`, `HealthData`, `HealthResponse`) forming the standardized response envelope.
- Phase 4: Added `GET /health` endpoint returning `{"data": {"status": "ok"}, "meta": {"timestamp": ..., "cached": false}}` using typed `response_model=HealthResponse`.
- Phase 4: Added 17 unit tests covering schemas, error envelope paths, and the health route.
- Phase 4: Added `GET /stocks`, `GET /stocks/{symbol}` endpoints — paginated list and per-symbol OHLCV history, backed by `PSXClient.historical()` with typed `response_model`.
- Phase 4: Added `GET /indices`, `GET /indices/{name}` endpoints — full index list and filtered records by index name.
- Phase 4: Added `GET /sectors`, `GET /sectors/{sector}` endpoints — sector summary list and per-sector filtering.
- Phase 4: Added `GET /market` endpoint — combined real-time trading panel data across all 15 board combinations.
- Phase 4: Added `PSXClient.symbols()` and top-level `psxdata.symbols()` for sector-filtered symbol lookup, used by the stocks router for symbol validation.
- Phase 4: Added 9 new Pydantic v2 response models to `api/schemas.py`: `StocksRow`, `StocksResponse`, `IndexRecord`, `IndicesResponse`, `SectorSummary`, `SectorsResponse`, `MarketRow`, `MarketResponse`, `SymbolsResponse`.

### Changed

- CI `lint` job now installs `.[dev,api]` so mypy can resolve FastAPI imports when checking `api/`.
- CI `test` job now ignores `tests/unit/api/` — API tests require FastAPI extras and run in the dedicated `test-api` job.
- `.gitignore` — fixed self-ignoring pattern; contributors now receive the file on clone. Personal paths moved to maintainer's global gitignore.
- `api/main.py` — replaced three ad-hoc exception handlers with five spec-compliant handlers; `PSXUnavailableError` → 503, `InvalidSymbolError` → 404, all errors return `{"error": {"status", "code", "message"}}` envelope.
- `api/routers/__init__.py` — registered `health_router`; switched from relative to absolute imports.
- `README.md`, `ARCHITECTURE.md`, `CONTRIBUTING.md` — updated API response envelope documentation to include `count` on list responses and the error envelope shape.
- `api/main.py` — registered all four new routers (`stocks`, `indices`, `sectors`, `market`) via `app.include_router()`.
- `api/requirements.txt` — pinned `psxdata==0.1.0a3` (exact prerelease pin required for pip to install without `--pre`); tightened all other deps to compatible-release specifiers (`~=`).
- `README.md` — added "Running the API with Docker" section with build, run, port-override, and health-check examples.

---

## [0.1.0a3] - 2026-04-20

### Added

- Phase 7: MkDocs + Material documentation site at https://psxdata.readthedocs.io — 12 pages covering getting started, 6 tutorial guides, full API reference, changelog, and contributing.
- Phase 7: `.readthedocs.yaml` v2 build config for Read the Docs free-tier hosting.
- Phase 7: `examples/quickstart.py` — runnable demo script covering all 5 core functions.
- Phase 7: Expanded all 8 module-level function docstrings (Args, Returns, Raises, Example) for clean API reference rendering via mkdocstrings.

### Changed

- `pyproject.toml`: added `docs` optional dependency group (`mkdocs-material`, `mkdocstrings[python]`), `Documentation` URL, and updated package description.

---

## [0.1.0a1] - 2026-04-19

First PyPI release. Core scraping library complete for all 8 PSX endpoints with caching, validation, and a clean public Python API.

### Added

- Phase 0: Probed all 8 PSX endpoints. Confirmed rendering modes — `/sector-summary` and `/financial-reports` require Playwright; all other endpoints work with plain `requests`.
- Phase 0: Captured HTML fixtures for all 5 key endpoints (`historical_engro`, `trading_panel`, `screener`, `sector_summary`, `financial_reports`).
- Phase 0: Added `tools/probe_endpoints.py` — reusable diagnostic that probes all PSX endpoints and writes `docs/PSX_ENDPOINTS.md`.
- Phase 0: Added `tools/capture_fixtures.py` — reusable fixture capture that saves stamped HTML snapshots to `tests/fixtures/`.
- Phase 0.5: Repository infrastructure — issue templates, PR template, CI/CD workflows, community files, GitHub labels, milestones, and development roadmap issues.
- Phase 2: Added `psxdata/exceptions.py` — 10-class exception hierarchy rooted at `PSXDataError`.
- Phase 2: Added `psxdata/constants.py` — all PSX endpoint URLs, request headers, retry/rate-limit config, cache settings, and full `COLUMN_MAP` from Phase 0 fixtures.
- Phase 2: Added `psxdata/utils.py` — `chunk_date_range` (configurable date splitter), `RateLimiter` (thread-safe, injectable clock), `validate_ohlc_dataframe` (flags/drops bad rows, adds `is_anomaly` column).
- Phase 2: Added `psxdata/parsers/normalizers.py` — `parse_date_safely` (never-raises, multi-format + fuzzy fallback), `coerce_numeric`, `normalize_column_name`.
- Phase 2: Added `psxdata/parsers/html.py` — dynamic HTML table parser using `COLUMN_MAP`; unknown headers fall back to `normalize_column_name` with a logged warning.
- Phase 2: Added `psxdata/cache/disk_cache.py` — `DiskCache` backed by `diskcache` + parquet; historical data never expires, today's data expires after 15 minutes.
- Phase 2: Added `psxdata/models/schemas.py` — 7 thin Pydantic v2 models: `OHLCVRow`, `Quote`, `IndexRecord`, `SectorSummary`, `TickerInfo`, `DebtInstrument`, `EligibleScrip`.
- Phase 2: Added `psxdata/scrapers/base.py` — `BaseScraper` with persistent session, exponential backoff retry, rate limiter, and Playwright context manager.
- Phase 3: Added scrapers for all 8 PSX endpoints — `historical.py` (POST, all-time OHLCV), `realtime.py` (15 trading-board combos), `indices.py` (18 indices), `sectors.py` (37 sectors), `fundamentals.py` (financial reports), `screener.py` (1000+ tickers with fundamentals), `debt_market.py` (4 instrument tables), `eligible_scrips.py` (9 category tables).
- Phase 3: Deprecated Playwright for scraping — all endpoints confirmed accessible via plain `requests`+BeautifulSoup. `_playwright_page()` retained in `BaseScraper` for tooling only.
- Phase 3 API: Added public package interface — `stocks()`, `tickers()`, `quote()`, `indices()`, `sectors()`, `fundamentals()`, `debt_market()`, `eligible_scrips()` exported from `psxdata/__init__.py`.
- Phase 5: Added full unit test suite — 80+ tests covering parsers, validators, cache, utils, and scraper reliability (mocked failure modes).
- Phase 5: Added integration test suite — real PSX endpoint tests for all 8 scrapers, marked `@pytest.mark.integration`.
- Phase 5: Added `tests/fixtures/` — static HTML/JSON snapshots for deterministic unit tests.
- Phase 6: Published to PyPI as `psxdata==0.1.0a1`.
- Phase 6: Added 5-job gated publish pipeline (`.github/workflows/publish.yml`) — tag verification → unit tests → build+twine check → TestPyPI → PyPI (manual approval gate).
- Phase 6: Removed `playwright` from core dependencies — optional tooling only.

### Changed

- Corrected `ARCHITECTURE.md` scraper→endpoint map: `/screener` and `/trading-panel` use `requests`+BeautifulSoup; `/sector-summary` and `/financial-reports` use Playwright.
- `CHANGELOG.md`: Added entries for Phases 3 through 6.

---

[Unreleased]: https://github.com/psxdata/psxdata/compare/v0.1.0a5...HEAD
[0.1.0a5]: https://github.com/psxdata/psxdata/compare/v0.1.0a4...v0.1.0a5
[0.1.0a4]: https://github.com/psxdata/psxdata/compare/v0.1.0a3...v0.1.0a4
[0.1.0a3]: https://github.com/psxdata/psxdata/compare/v0.1.0a2...v0.1.0a3
[0.1.0a2]: https://github.com/psxdata/psxdata/compare/v0.1.0a1...v0.1.0a2
[0.1.0a1]: https://github.com/psxdata/psxdata/releases/tag/v0.1.0a1
