# psxdata — Python Library for Pakistan Stock Exchange (PSX) Data

[![CI](https://github.com/psxdata/psxdata/actions/workflows/ci.yml/badge.svg)](https://github.com/psxdata/psxdata/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/psxdata)](https://pypi.org/project/psxdata/)
[![PyPI Downloads](https://static.pepy.tech/personalized-badge/psxdata?period=total&units=INTERNATIONAL_SYSTEM&left_color=GREY&right_color=GREEN&left_text=downloads)](https://pepy.tech/projects/psxdata)
[![Documentation](https://img.shields.io/badge/docs-mintlify-blue)](https://psxdata.mintlify.app)
[![Python](https://img.shields.io/pypi/pyversions/psxdata)](https://pypi.org/project/psxdata/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**[Full documentation at psxdata.mintlify.app](https://psxdata.mintlify.app)**

> **Deprecated:** ReadTheDocs hosting at [psxdata.readthedocs.io](https://psxdata.readthedocs.io) is no longer the primary documentation source and may be removed in a future release.

**psxdata** is a Python library for downloading Pakistan Stock Exchange (PSX) data — historical OHLCV prices, real-time quotes, KSE-100 index constituents, sector summaries, fundamentals, debt market instruments, and margin-eligible stocks. Free, open-source, and actively maintained.

<details>
<summary>Alpha release note</summary>

`0.1.0a1` — Core scraping, caching, and public API are complete. The FastAPI REST layer has moved to [psxdata/psxdata-api](https://github.com/psxdata/psxdata-api). APIs may change before `1.0`.

</details>

---

## Installation

```bash
pip install psxdata
```

Requires Python 3.11+. For SOCKS proxy support, install the optional extra:

```bash
pip install "psxdata[socks]"
```

---

## Quick Start

```python
import psxdata

# Historical OHLCV data
df = psxdata.stocks("ENGRO", start="2024-01-01", end="2024-12-31")

# All listed tickers
all_tickers = psxdata.tickers()

# KSE-100 index constituents
kse100 = psxdata.indices("KSE100")

# Live quote
q = psxdata.quote("LUCK")

# Sector summary
sectors = psxdata.sectors()

# Debt market instruments
debt = psxdata.debt_market()

# Margin-eligible stocks
scrips = psxdata.eligible_scrips()
```

---

## API Reference

| Function                               | Description                                      |
| -------------------------------------- | ------------------------------------------------ |
| `psxdata.stocks(symbol, start, end)` | Historical OHLCV DataFrame for a ticker          |
| `psxdata.tickers()`                  | All listed tickers (1000+)                       |
| `psxdata.symbols()`                  | Symbol/sector/name metadata, optionally filtered |
| `psxdata.quote(symbol)`              | Live quote row for a ticker                      |
| `psxdata.screener()`                 | Full, unfiltered screener table (~729 symbols)   |
| `psxdata.indices(name)`              | Constituents of a named index (e.g.`"KSE100"`) |
| `psxdata.sectors()`                  | Sector aggregates DataFrame (37 sectors)         |
| `psxdata.fundamentals(symbol)`       | Financial reports for a ticker                   |
| `psxdata.debt_market()`              | Debt market instruments (TFCs, Sukuks, etc.)     |
| `psxdata.eligible_scrips()`          | Margin trading eligible stocks                   |
| `psxdata.configure(proxy=...)`       | Set a proxy for the module-level functions       |

---

## Using a Proxy

Route every request psxdata makes to PSX, including the `X-Req-Id` token fetch, through a proxy of your choice:

```python
import psxdata
from psxdata import PSXClient

# Per client: http://, https://, or socks5:// (with psxdata[socks]), credentials allowed
client = PSXClient(proxy="http://user:pass@proxy.example.com:8080")
df = client.stocks("ENGRO", start="2024-01-01")

# Module-level functions
psxdata.configure(proxy="socks5://127.0.0.1:1080")
df = psxdata.stocks("ENGRO")

# Separate proxies per scheme, same shape as requests' `proxies` dict
client = PSXClient(proxy={"http": "http://p:8080", "https": "http://p:8443"})
```

- With no `proxy`, behaviour is unchanged and the standard `HTTP_PROXY` / `HTTPS_PROXY` environment variables still apply. An explicit `proxy` takes precedence over them.
- Proxy credentials are never logged. To confirm the proxy is in use, enable debug logging (`logging.getLogger("psxdata").setLevel(logging.DEBUG)`): each request logs `via proxy http://***@host:port`.
- If the proxy can't be reached, `PSXConnectionError` is raised and its message names the proxy, with credentials hidden.
- Rate limiting and PSX request-token handling apply exactly as they do without a proxy.

---

## Why psxdata

Existing solutions for PSX data tend to hardcode date formats and column positions that break silently when PSX changes its HTML. `psxdata` is designed differently:

- **Dynamic column extraction** from `<th>` tags — survives column reordering
- **Multi-format date parsing** with fuzzy fallback via `dateutil`
- **Exponential backoff retries** — 3 attempts, 1s/2s delays
- **Disk cache** (`~/.psxdata/cache/`) — historical data cached forever, live data for 15 min
- **Data validation** — OHLC constraint checks, duplicate/future date detection

---

## Data Availability

`psxdata` supports **daily historical OHLCV bars** and **live quote snapshots** only. Intraday historical data (1-minute, 5-minute, 15-minute bars, etc.) is not available because PSX does not publicly expose historical intraday data through any official channel — the DPS/KATS feeds only provide real-time data, not a historical intraday archive. If PSX exposes such an endpoint in the future, support may be added.

---

## REST API

A FastAPI REST service wrapping this library now lives in a standalone repository: **[psxdata/psxdata-api](https://github.com/psxdata/psxdata-api)**.

It exposes the same data as this library over HTTP (`GET /stocks`, `GET /indices/{name}`, `GET /sectors`, etc.), installs `psxdata` from PyPI, and ships its own Docker image (`mtauha/psxdata-api` on Docker Hub) and CI/CD pipeline. See that repo's README for endpoints, request/response formats, and Docker run instructions.

---

## Development Status

See the [roadmap issue](https://github.com/psxdata/psxdata/issues/4) for the full phase breakdown.

- ✅ Phase 0 — PSX endpoint research and HTML fixture capture
- ✅ Phase 0.5 — Repository setup, CI/CD, community files
- ✅ Phase 2 — Core engineering (BaseScraper, parsers, cache, utils)
- ✅ Phase 3 — Scrapers (historical, real-time, indices, sectors, fundamentals, screener, debt, eligible scrips)
- ✅ Phase 3 API — Public Python package interface
- ✅ Phase 4 — FastAPI REST layer (now at [psxdata/psxdata-api](https://github.com/psxdata/psxdata-api))
- ✅ Phase 5 — Full test suite (API layer tests pending)
- ✅ Phase 6 — Packaging & PyPI publish
- ✅ Phase 7 — Documentation

---

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) and open an issue before starting non-trivial work.

---

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for the component diagram, data flow, and design decisions.
