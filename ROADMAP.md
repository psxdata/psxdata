# psxdata — Development Roadmap

> **Status:** Active development — through Phase 3 API complete. Phases 4 and 5 are open for contributions.

This file is the single source of truth for where `psxdata` is and where it is going. The [ROADMAP issue (#4)](https://github.com/psxdata/psxdata/issues/4) on GitHub tracks overall progress.

---

## At a Glance

```
Phase 0     ✅  PSX endpoint research & fixture capture
Phase 0.5   ✅  Repository setup, CI/CD, community files
Phase 2     ✅  Core engineering (BaseScraper, parsers, cache, utils)
Phase 3     ✅  All 8 PSX endpoint scrapers
Phase 3 API ✅  Public Python package interface
─────────────────────────────────────────────────────────────────
Phase 4     ➡️  FastAPI REST layer (moved to psxdata/psxdata-api)
Phase 5     🔲  Full test suite               ← open for contributions
Phase 6     🔲  Packaging, Docker, CI/CD      ← depends on 4 + 5
Phase 7     🔲  Documentation                 ← can start alongside 6
```

---

## Completed Phases

### ✅ Phase 0 — PSX Endpoint Research

Discovered and documented all 8 PSX AJAX endpoints. Captured live HTML fixtures. Wrote schema drift tooling (`tools/probe_endpoints.py`).

Artifacts: `docs/PSX_ENDPOINTS.md`, `tools/`

### ✅ Phase 0.5 — Repository Bootstrap

CI/CD (GitHub Actions), branch protection, labels, milestones, and all community files (`CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, `LICENSE`).

Artifacts: `.github/`, `pyproject.toml`, community files

### ✅ Phase 2 — Core Engineering ([#5](https://github.com/psxdata/psxdata/issues/5))

| Component | What it does |
|---|---|
| `exceptions.py` | Custom exception hierarchy |
| `constants.py` | All PSX URLs and magic values |
| `utils.py` | Date chunker, rate limiter, OHLC validators |
| `parsers/normalizers.py` | Multi-format date parsing, type coercion |
| `parsers/html.py` | Dynamic `<th>`-driven column extraction |
| `cache/disk_cache.py` | Parquet-backed disk cache with TTL |
| `models/schemas.py` | Pydantic v2 data models |
| `scrapers/base.py` | `BaseScraper` — session, retry, rate limit |

### ✅ Phase 3 — Scrapers ([#6](https://github.com/psxdata/psxdata/issues/6))

| Scraper | Endpoint |
|---|---|
| `historical.py` | POST `/historical` — OHLCV |
| `realtime.py` | GET `/trading-board/{market}/{board}` |
| `screener.py` | GET `/screener` |
| `symbols.py` | GET `/symbols` (JSON) |
| `indices.py` | GET `/indices/{name}` |
| `sectors.py` | GET `/sector-summary/sectorwise` |
| `fundamentals.py` | GET `/financial-reports-list` |
| `debt_market.py` | GET `/debt-market` |
| `eligible_scrips.py` | GET `/eligible-scrips` |

### ✅ Phase 3 API — Public Python Interface ([#7](https://github.com/psxdata/psxdata/issues/7))

`psxdata/client.py` with `PSXClient` and module-level convenience functions:

```python
import psxdata

psxdata.stocks("ENGRO", start="2024-01-01", end="2024-12-31")
psxdata.tickers(index="KSE-100")
psxdata.indices()
psxdata.sectors()
psxdata.fundamentals("ENGRO")
psxdata.market.debt()
psxdata.market.eligible_scrips()
```

---

## Active & Upcoming Phases

> **Parallel tracks:** Phases 4 and 5 are independent — contributors can work on either simultaneously.

---

### Track A

#### ➡️ Phase 4 — FastAPI REST Layer (moved to [psxdata/psxdata-api](https://github.com/psxdata/psxdata-api)) ([#8](https://github.com/psxdata/psxdata/issues/8))

This phase has moved to its own repository: [psxdata/psxdata-api](https://github.com/psxdata/psxdata-api). It consumes `psxdata` as a published PyPI dependency. The sub-tasks below are kept for historical reference and remain linked to their original issues.

Build `api/` wrapping the Python package. All responses follow:

```json
{ "data": ..., "meta": { "timestamp": "...", "cached": true } }
```

**Sub-tasks:**

| # | Task | Difficulty | Notes |
|---|---|---|---|
| 4.1 | FastAPI app skeleton — `api/main.py`, lifespan, middleware, global error handlers | `good first issue` | Follow patterns in `api/routers/__init__.py` |
| 4.2 | `GET /health` endpoint | `good first issue` | Returns `{"status": "ok"}` |
| 4.3 | `GET /stocks` and `GET /stocks?index=` endpoints | `help wanted` | Calls `psxdata.tickers()` |
| 4.4 | `GET /stocks/{symbol}/historical?start=&end=` | `help wanted` | Calls `psxdata.stocks()`, raise 404 for unknown symbol |
| 4.5 | `GET /stocks/{symbol}/quote` | `help wanted` | Calls `psxdata.quote()` |
| 4.6 | `GET /stocks/{symbol}/fundamentals` | `help wanted` | Calls `psxdata.fundamentals()` |
| 4.7 | `GET /indices` and `GET /indices/{name}/historical` | `help wanted` | Calls `psxdata.indices()` |
| 4.8 | `GET /sectors` and `GET /sectors/{name}/stocks` | `help wanted` | Calls `psxdata.sectors()` |
| 4.9 | `GET /debt-market` and `GET /eligible-scrips` | `help wanted` | Calls `psxdata.market.*` |
| 4.10 | `slowapi` rate limiting — 60 req/min/IP | medium | Add to `api/dependencies.py` |
| 4.11 | CORS middleware — allow all origins | `good first issue` | One-liner in `main.py` |
| 4.12 | Standardized error responses — 404, 503, 429 | medium | Global exception handlers |
| 4.13 | Optional Redis caching layer with in-memory fallback | complex | Log warning when Redis unavailable |
| 4.14 | `Dockerfile` for FastAPI service | `good first issue` | Python 3.11-slim base, no Playwright |

---

#### 🔲 Phase 5 — Full Test Suite ([#9](https://github.com/psxdata/psxdata/issues/9))

Complete unit, integration, and reliability coverage. **No Playwright needed** — all fixtures are static HTML from AJAX responses.

**Test pyramid target:**

```
~5  API contract tests   — HTTP round-trips via TestClient
~30 Integration tests    — real PSX endpoints, network required
~80 Unit tests           — parsers, validators, cache, utils
```

**Sub-tasks:**

| # | Task | Difficulty | Notes |
|---|---|---|---|
| 5.1 | Unit tests — `parsers/normalizers.py::parse_date_safely` | `good first issue` | See test cases table in `CLAUDE.md` |
| 5.2 | Unit tests — `parsers/html.py` column mapper | `good first issue` | Edge cases: missing col, extra col, empty table |
| 5.3 | Unit tests — `utils.py` OHLC validators | `good first issue` | Valid + invalid OHLC, negative volume, NaN |
| 5.4 | Unit tests — `utils.py` date range chunker | `good first issue` | Single day, 5-year range, `start > end` raises |
| 5.5 | Unit tests — `cache/disk_cache.py` | medium | Cache miss, write-read round-trip, TTL expiry (mock time) |
| 5.6 | Unit tests — `PSXClient` public functions | medium | Mock scrapers, verify cache lookup path |
| 5.7 | HTML fixtures — capture static responses for all 8 endpoints | `good first issue` | Run `tools/capture_fixtures.py`, commit to `tests/fixtures/` |
| 5.8 | Integration tests — all 8 scrapers against live PSX | `help wanted` | Mark `@pytest.mark.integration`, use ENGRO/LUCK/HBL |
| 5.9 | Reliability tests — retry/backoff simulation | medium | Mock `Session.post` to raise `Timeout`, verify retry |
| 5.10 | Reliability tests — partial chunk failure | medium | 2 of 5 futures raise exception; verify partial data returned |
| 5.11 | Reliability tests — PSX 503 and empty HTML | medium | Mock all requests to return 503; empty `<html>` response |
| 5.12 | Reliability tests — rate limiter enforcement | medium | 10 requests with mocked clock; verify ≤ 2/s |
| 5.13 | API layer tests — TestClient for all routes | `help wanted` | Mock library layer; test 200, 404, 503, 429, CORS |
| 5.14 | Schema drift detection — `probe_endpoints.py --diff` | complex | Detect column rename/removal against captured fixtures |

---

### Track B — starts after Track A is mostly complete

#### 🔲 Phase 6 — Packaging, Docker & CI/CD ([#10](https://github.com/psxdata/psxdata/issues/10))

**Sub-tasks:**

| # | Task | Difficulty | Notes |
|---|---|---|---|
| 6.1 | Finalize `pyproject.toml` — classifiers, keywords, URLs | `good first issue` | Add PyPI trove classifiers |
| 6.2 | PyPI publish GitHub Actions workflow | medium | Trigger on version tag push |
| 6.3 | `docker-compose.yml` for FastAPI + optional Redis | medium | Exposes port 8000 |
| 6.4 | Dependabot configuration for pip + GitHub Actions | `good first issue` | `.github/dependabot.yml` |
| 6.5 | Scheduled schema-drift CI check | medium | Weekly cron job calling `probe_endpoints.py --diff` |
| 6.6 | Move `playwright` to optional dev dependency | `good first issue` | `pip install psxdata[dev]` only |

---

#### 🔲 Phase 7 — Documentation ([#11](https://github.com/psxdata/psxdata/issues/11))

Can begin as soon as Phase 4 API surface is stable.

**Sub-tasks:**

| # | Task | Difficulty | Notes |
|---|---|---|---|
| 7.1 | README — working install + usage examples | `good first issue` | Replace "planned API" section with real code |
| 7.2 | Docstrings for all public functions in `client.py` | `good first issue` | NumPy-style docstrings |
| 7.3 | Docstrings for all scraper classes | `good first issue` | Include which endpoint each scraper targets |
| 7.4 | Auto-generated API reference (mkdocs or sphinx) | medium | Auto-build from docstrings in CI |
| 7.5 | FastAPI Swagger/ReDoc smoke-test in CI | `good first issue` | Assert `GET /docs` returns 200 |
| 7.6 | Update `ARCHITECTURE.md` — finalize component diagram | medium | Reflect AJAX-only, no Playwright |
| 7.7 | Usage example script or notebook | `good first issue` | `examples/quickstart.py` demonstrating all public functions |

---

## How to Contribute

**New here?** Start with tasks marked `good first issue` above — they are well-scoped and don't require deep knowledge of PSX internals.

**Want something bigger?** Look for `help wanted` tasks — clearly defined work where outside contributions are actively welcome.

**Before opening a PR:**
1. Read [CONTRIBUTING.md](CONTRIBUTING.md)
2. Open a GitHub issue (or comment on an existing one) to claim the work
3. Branch from `main` using the naming convention in CONTRIBUTING.md

---

## Dependency Map

```
Phase 2 ✅
  └── Phase 3 ✅
        └── Phase 3 API ✅
              ├── Phase 4 🔲 ──┐
              └── Phase 5 🔲 ──┴── Phase 6 🔲
                                       └── Phase 7 🔲 (can overlap with 6)
```

Phases 4 and 5 are independent — they can run fully in parallel. Phase 6 should wait until Phase 4 produces a shippable package. Phase 7 can begin as soon as the Phase 4 API surface is stable enough to document.

---

## Architecture Quick Reference

```
PSX Servers ──► BaseScraper ──► Parsers ──► Validators ──► DiskCache
                                                                │
                                                           PSXClient
                                                                │
                                                           FastAPI (Phase 4)
```

All PSX endpoints are plain HTTP (AJAX) — no browser automation required for normal use. See [ARCHITECTURE.md](ARCHITECTURE.md) for the full component diagram.
