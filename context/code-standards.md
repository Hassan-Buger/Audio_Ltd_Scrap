# Code Standards

## General Principles

- Use Python 3.12+ unless Railway/runtime compatibility testing requires a documented adjustment.
- Prefer simple, explicit, typed code over clever abstractions.
- Keep modules small and single-purpose.
- Fix root causes; do not hide failures with broad exception handlers or silent fallbacks.
- Separate HTTP fetching, HTML extraction, normalization, validation, persistence, orchestration, and presentation.
- Keep extraction functions deterministic and independently testable.
- Make operations idempotent wherever retries or repeated discovery can occur.
- Use UTC timestamps in storage. Convert to local time only for presentation.
- Use `Decimal` for monetary values; never use binary floating point for prices.
- Use explicit enums/constants for lifecycle states and URL types.
- Preserve raw source values when normalization may lose information.
- Do not add dependencies without a clear need and an update to the dependency manifest.
- Do not introduce Firecrawl.

## Python Conventions

- Use type hints for public functions, class attributes, and service boundaries.
- Use Pydantic models for external/configuration boundaries and typed extraction contracts where appropriate.
- Use `dataclass` for simple internal immutable value objects when Pydantic behavior is unnecessary.
- Follow PEP 8 and use a consistent formatter/linter configuration (choose Ruff unless an existing project standard supersedes it).
- Prefer `pathlib.Path` over manual path concatenation.
- Use context managers for database sessions, files, browser resources, and network resources.
- Use structured logging; do not use `print()` in application code.
- Do not catch `Exception` unless the boundary can log context, classify the failure, and preserve correct state.
- Catch specific exceptions at the narrowest sensible boundary.
- Never use `except: pass`.
- Avoid module-level mutable state.
- Keep secrets out of constants and test fixtures.

## FastAPI Conventions

- Keep route handlers thin: validate input, call a service/use case, and map the result to an HTTP response.
- Do not run Scrapy crawls, browser sessions, translations, or other long-running work inside request handlers.
- Use dependency injection for database sessions and authenticated operator context.
- Define explicit Pydantic request and response schemas.
- Use consistent status codes and error response structure.
- Return `202 Accepted` when a crawl job is accepted for background processing.
- Use `404` for unknown resources, `409` for invalid state transitions/conflicts, `422` for invalid input, and `503` for unavailable dependencies where appropriate.
- Paginate collection endpoints and cap page sizes.
- Allowlist sort fields and filter operations; never interpolate arbitrary client values into SQL.
- Version API changes deliberately and document breaking changes.
- Keep health/liveness and readiness semantics separate.

## Scrapy and Crawler Conventions

- Scrapy is the primary HTTP fetching engine.
- Keep spiders focused on discovery and orchestration; delegate parsing to extraction modules and persistence to pipelines/repositories.
- Do not duplicate parser logic across spiders.
- Set explicit timeouts, concurrency, retry policy, per-domain delay, and request headers consistent with site policy.
- Respect robots directives and applicable site terms. Do not bypass access controls or anti-bot measures.
- Normalize URLs in one tested utility. Preserve meaningful query parameters such as page numbers and search terms.
- Record source URL, canonical URL, crawl job, run, parser version, and discovery path where available.
- Prevent pagination loops and repeated URL scheduling.
- Use Playwright only through `app/browser/` and only for pages demonstrated to need it.
- Close browser pages, contexts, and processes reliably, including on cancellation and exceptions.
- Do not rely on Scrapy's local JOBDIR as the sole durable frontier in Railway.

## Extraction and Data Quality

- Separate extraction from normalization and validation.
- Keep selectors and parsing rules in named functions or page-specific parser modules, not scattered through route handlers.
- Treat all external page content as untrusted input.
- Preserve the exact source text before normalization where practical.
- Store numeric specification value and unit separately only when the source representation supports that interpretation; also retain the raw displayed value.
- Never infer a missing SKU, EAN, model, price, stock status, or specification.
- Use field-level validation findings; one missing optional field should not necessarily discard an otherwise valid product.
- Distinguish “not present on page,” “not parsed,” “invalid,” and “not checked.”
- Build parser tests from saved, sanitized HTML fixtures that represent actual observed page structures.
- Keep fixture provenance (page type, capture date, relevant URL pattern) documented.

## SQLAlchemy and Database Rules

- Use SQLAlchemy 2 style and explicit model/repository boundaries.
- Use Alembic for every schema change; do not edit production schema manually.
- Keep transaction ownership clear. Repositories should not unexpectedly commit unrelated work.
- Use database constraints for identity and referential integrity where possible.
- Use explicit unique/index definitions and document their purpose.
- Use `Decimal` for money and timezone-aware timestamps.
- Use `ON CONFLICT`/upsert patterns only where their identity semantics are understood and tested.
- Make product/category/source relationships idempotent.
- Do not delete historical provenance when updating a canonical product.
- Claim frontier rows transactionally; use leases or claim expiry to recover abandoned work.
- Never mark a URL processed before the extraction/persistence outcome is safely committed.

## Celery and Job Lifecycle

- Task payloads should carry stable identifiers, normally a job ID or batch ID, not large mutable state objects.
- Treat task delivery as potentially duplicated; tasks must be idempotent.
- Persist authoritative state transitions in PostgreSQL.
- Use bounded retries with exponential backoff and jitter where appropriate.
- Classify retryable versus terminal failures.
- Make pause, resume, and cancel requests explicit persisted states; document how quickly they take effect.
- Acknowledge tasks only after durable progress has been recorded according to the chosen Celery delivery configuration.
- Do not assume a task will run exactly once.
- On worker startup, reconcile queued and expired-lease work with the task broker.

## Translation Rules

- Translation is a separate service and data lifecycle.
- Never overwrite source-language fields.
- Preserve identifiers, brand names, model names, numbers, dimensions, units, and technical codes.
- Store language metadata and translation provenance.
- Make translation optional and independently retryable.
- A translation failure must not invalidate source extraction.

## Dashboard and UI Conventions

- Use Jinja2 templates and HTMX for interactions; do not add a SPA framework in the first release.
- Keep templates focused and use shared partials for repeated UI.
- Escape all untrusted source content by default.
- Do not render scraped HTML as trusted markup.
- Show source values distinctly from translated values.
- Display clear empty, loading, error, and partial-data states.
- Show the denominator and definition for every coverage percentage.
- Confirm destructive or state-changing actions such as cancel/retry where appropriate.
- Ensure forms include CSRF protection if cookie-based authentication is used.
- Use the design tokens in `ui-context.md`; do not scatter raw colors or arbitrary spacing values.

## API and Security

- Validate all request parameters before use.
- Enforce authentication and authorization on every mutation.
- Apply host allowlists to user-supplied crawl URLs.
- Defend against SSRF: reject localhost, private, link-local, metadata, and non-HTTP(S) destinations unless an explicit safe development-only exception is implemented.
- Avoid exposing arbitrary file paths or filesystem access through export endpoints.
- Stream exports safely and cap expensive query sizes.
- Redact credentials, cookies, authorization headers, and sensitive query parameters from logs.
- Set secure production cookie flags and HTTPS-only behavior where applicable.
- Do not commit real `.env` files.

## Testing Standards

- Use Pytest.
- Unit-test URL normalization, pagination detection, category parsing, product extraction, specification parsing, and deduplication.
- Use fixtures from actual observed pages; do not fabricate HTML fixtures that imply unverified site structure.
- Test missing/partial fields and malformed content.
- Test repeated discovery and duplicate task delivery.
- Test worker restart/lease recovery and Redis dispatch recovery.
- Test database migrations on a clean database and an upgrade path.
- Test API validation, authorization, pagination, error responses, and export content types.
- Use controlled integration tests; live target-site tests must be opt-in and rate-limited.
- Do not make normal CI depend on the target website being online.

## File Organization

- `app/api/` — FastAPI route modules and API dependencies.
- `app/dashboard/` — dashboard routes, templates, static files and view models.
- `app/crawler/` — Scrapy spiders, settings, middleware, scheduler adapters and pipelines.
- `app/extraction/` — pure parsing and extraction functions.
- `app/browser/` — Playwright-only browser lifecycle and helpers.
- `app/database/models/` — ORM models.
- `app/database/repositories/` — database persistence and query logic.
- `app/services/` — use cases and domain services.
- `app/tasks/` — Celery configuration and task entry points.
- `app/schemas/` — Pydantic schemas and shared data contracts.
- `migrations/` — Alembic migrations.
- `tests/` — unit, integration, fixture and end-to-end tests.
- `context/` — persistent project context and specifications.
- `config/` — non-secret operational configuration.
