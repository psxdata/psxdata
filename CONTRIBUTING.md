# Contributing to psxdata

Thank you for your interest in contributing. This guide covers everything you need to get started.

---

## Getting Started

```bash
git clone https://github.com/psxdata/psxdata.git
cd psxdata

python -m venv .venv
source .venv/bin/activate       # Linux/Mac
.venv\Scripts\activate          # Windows

pip install -e ".[dev]"
```

Verify your setup:

```bash
pytest tests/unit/ -v           # Should pass (no network required)
ruff check psxdata/              # Should return no errors
```

> **Looking to contribute to the REST API?** That code now lives in [psxdata/psxdata-api](https://github.com/psxdata/psxdata-api) — open issues and PRs there instead.

---

## Issue First Policy

Before starting any non-trivial change, open a GitHub issue. This prevents duplicate work and lets maintainers give early feedback on direction. Issues are free — PRs without a linked issue may be closed without review.

Exceptions: typo fixes, documentation corrections, and test-only changes that fix an already-filed bug.

---

## Branch Naming

```
feat/short-description      # new feature
fix/short-description       # bug fix
docs/short-description      # documentation only
chore/short-description     # maintenance, refactor, infra
```

Always branch from `main`:

```bash
git checkout main
git pull
git checkout -b feat/your-feature
```

Never commit directly to `main`.

---

## PR Process

1. Fork the repository (external contributors) or branch directly (maintainers)
2. Make your changes on a feature branch
3. Run the test suite locally — see [TESTING.md](TESTING.md)
4. Open a PR targeting `main`
5. Fill in the PR template completely
6. Link the related issue with `Closes #N` in the PR body

PRs require at least one approving review and passing CI (`lint` + `test` jobs) before merge.

---

## Commit Messages

Conventional commits are encouraged but not enforced:

```
feat: add historical data caching
fix: handle empty table response from /screener
docs: update endpoint map in ARCHITECTURE.md
chore: bump ruff to 0.5
```

Keep the subject line under 72 characters. Use the body to explain *why*, not *what*.

---

## Testing

Unit tests are required for any new utility, parser, or validator function. Integration tests are required for any new scraper. See [TESTING.md](TESTING.md) for the full guide.

The test suite runs in two separate environments to match their dependency footprints:

**Core (scraper/parser/cache)** — installs `.[dev]` only:

```bash
pytest tests/unit/ --ignore=tests/unit/api -v   # run before every commit
pytest -m integration -v                         # run before scraper PRs
pytest tests/unit/ --ignore=tests/unit/api --cov=psxdata --cov-report=term-missing
```

**API layer** — requires `.[dev,api]` (FastAPI, uvicorn, slowapi):

```bash
pip install -e ".[dev,api]"
pytest tests/unit/api/ -v
```

Never add FastAPI imports to `tests/unit/` outside of `tests/unit/api/` — those tests run without the API extras installed.

---

## Code Standards

- Type hints on all public functions
- Docstrings on all public functions (one-line minimum)
- `ruff check` must pass with zero errors
- `mypy` must pass with zero errors on the modules you changed
- No hardcoded date formats — always use `parse_date_safely()` from `parsers/normalizers.py`
- No fixed column positions — always map by `<th>` name, never by index
- The FastAPI app requires an editable install to use package-style imports. Do not add `sys.path` fallbacks in `api/*`.
---

## Adding a New Scraper

1. Inherit from `BaseScraper` in `psxdata/scrapers/base.py`
2. Add a comment at the top declaring the scraping mode and why
3. Use `parse_date_safely()` — never hardcode date formats
4. Extract columns dynamically from `<th>` tags — never assume fixed positions
5. Validate returned data using the validators in `utils.py`
6. Write unit tests for any new helper functions first
7. Write an integration test hitting the real PSX endpoint
8. If using Playwright: capture an HTML fixture with `python tools/capture_fixtures.py`

---

## Adding a New API Endpoint

1. Create `api/routers/{data_type}.py` — one file per data type
2. Register the router in `api/routers/__init__.py`:
   ```python
   from .your_module import router as your_router
   router_registry: list[APIRouter] = [..., your_router]
   ```
3. Declare `tags=` on the `APIRouter` for docs grouping
4. Use a fully-typed `response_model` — `dict[str, str]` not `dict`
5. All responses must follow the approved envelope spec:
   - List endpoint:   `{"data": [...], "meta": {"timestamp": "...", "cached": bool, "count": N}}`
   - Single-item:    `{"data": {...}, "meta": {"timestamp": "...", "cached": bool}}`
   - Named tables:   `{"data": {"table_0": [...], ...}, "meta": {"timestamp": "...", "cached": bool}}`
   - Error:          `{"error": {"status": 404, "code": "not_found", "message": "..."}}`

   Use `MetaSingle` / `MetaList` from `api/schemas.py`. Never construct meta dicts by hand.
   Error codes: `bad_request` (400/422), `not_found` (404), `rate_limited` (429),
                `psx_unavailable` (503), `internal_error` (500).
6. Map HTTP errors explicitly:
   - `404` — unknown symbol or resource not found
   - `503` — PSX unreachable or library raised `PSXUnavailableError`
   - `429` — handled by `slowapi`; do not re-raise manually
7. Inject shared dependencies from `api/dependencies.py` via `Depends()` — never instantiate cache or rate limiter inside a route function
8. Write a unit test using `TestClient`. Declare the fixture at module level, not inside the test body:
   ```python
   @pytest.fixture
   def client() -> TestClient:
       return TestClient(app)
   ```
9. Mock the library layer in unit tests — do not hit real PSX servers from `tests/unit/`

---

## Raising a PSX Endpoint Change

If PSX changes a page structure and a scraper breaks, open an issue using the **Endpoint Change** template. Include the endpoint URL, what changed, and which scraper is affected. Add an inline comment to the broken code referencing the issue number: `# TODO(#N): brief description`.
