# Audiovideo.lt Product Scraper

## Overview

Audiovideo.lt Product Scraper is a Python-based data collection application for discovering and extracting publicly accessible product catalogue information from [audiovideo.lt](https://www.audiovideo.lt/). It is intended for an operator who needs broad, repeatable coverage of product categories, nested categories, manufacturer listings, search results, pagination, and individual product pages. The application stores normalized data in PostgreSQL, preserves original Lithuanian content, keeps English translations separately, exposes a REST API, and provides a web dashboard for controlling jobs, reviewing results, monitoring coverage, and exporting data. It is deployed on Railway. The system must maximize lawful and technically accessible coverage without claiming that inaccessible or undiscovered pages have been scraped.

## Product Goals

1. Discover parent categories, child categories, nested subcategories, manufacturer listings, search-result listings, pagination links, and product detail URLs reachable from configured seed URLs.
2. Extract product identity and catalogue data accurately, including source title, description, SKU, EAN/GTIN where present, manufacturer/brand, model, price, currency, availability text, images, product URL, category relationships, and structured specifications.
3. Preserve source-language Lithuanian values as the authoritative source record; store English translations in separate fields or translation records without overwriting source content.
4. Deduplicate products across category, manufacturer, search, and direct-URL discovery paths while retaining every known source and category relationship.
5. Persist crawl state and results durably so jobs can resume after worker restarts or Railway redeployments.
6. Provide a REST API and web dashboard for starting, inspecting, controlling, and reporting on scraping jobs.
7. Export product data and reports in JSON and CSV formats.
8. Make coverage measurable and auditable: distinguish discovered, queued, attempted, processed, extracted, incomplete, failed, skipped, and inaccessible URLs/records.

## Primary User and Core Need

The primary user is the project owner/operator. The core need is to collect and maintain a large, structured product catalogue from publicly accessible Audiovideo.lt pages, understand what was and was not collected, and retrieve the data through an API, dashboard, or export.

## Core User Flow

1. The operator opens the dashboard and reviews the latest job status, catalogue totals, and coverage report.
2. The operator starts a new crawl using one or more configured seed URLs, a selected crawl scope, or a full-discovery mode.
3. The application validates the request, creates a durable crawl job, and records its initial URL frontier in PostgreSQL.
4. A background worker claims eligible URLs, fetches pages using Scrapy, parses listing/detail data, and records discovered URLs and relationships.
5. The crawler follows allowed category, manufacturer, search, pagination, and product links within configured scope and safety limits.
6. Playwright is used only as a controlled fallback when a page requires browser rendering and the normal HTTP response is insufficient.
7. Extracted records are validated, normalized, deduplicated, and persisted. Lithuanian source values remain unchanged; translation work is stored separately.
8. The operator monitors progress, inspects incomplete or failed records, and retries eligible failures.
9. The operator queries products and categories through the dashboard or REST API.
10. The operator downloads JSON/CSV exports and coverage reports.

## Initial Seed URLs

Treat these as starting points, not as an exhaustive URL list:

- `https://www.audiovideo.lt/automobiliu-garso-aparatura/garso-izoliacija?p=1`
- `https://www.audiovideo.lt/gamintojai/hertz`
- `https://www.audiovideo.lt/catalogsearch/result/?cat=0&q=audison`
- `https://www.audiovideo.lt/catalogsearch/result/?cat=0&q=bass+habit`

The crawler should also support operator-supplied URLs. Validate host scope and URL policy before enqueueing them.

## Features

### Discovery and Crawling

- Recursive category and nested-subcategory discovery.
- Manufacturer/brand listing discovery.
- Search-result listing discovery for configured queries and URLs.
- Pagination discovery and termination detection.
- Product-detail URL discovery and extraction.
- Canonical URL handling and query-parameter normalization rules, established from observed site behavior.
- Configurable crawl depth, URL limits, concurrency, delay, and allowed URL patterns.
- Durable frontier with restart recovery and incremental recrawling.

### Product Data

- Product title and description in the original source language.
- SKU, EAN/GTIN, model, manufacturer/brand, and other identifiers where present.
- Price, currency, unit, availability text, and price observation timestamp where present.
- Product image URLs and source product URL.
- Structured technical specifications with original labels, values, and units.
- Category and manufacturer relationships.
- Provenance linking each extracted value or record to the page and crawl run that produced it.
- Separate English translation data; no destructive translation of source fields.

### Operations and Visibility

- REST API for jobs, categories, products, reports, and exports.
- Web dashboard for job creation and control, progress, product browsing, category browsing, failures, incomplete records, and exports.
- Durable pause/resume/cancel state where supported by the worker lifecycle.
- Retry controls for eligible failures.
- Structured logs and actionable error records.
- Historical job and coverage reports.

### Data Quality

- Field-level validation and completeness assessment.
- Duplicate detection that protects distinct product variants.
- Explicit missing/null values instead of invented data.
- Reconciliation of discovered listing counts against extracted unique products where reliable source counts are available.
- Tests using saved HTML fixtures and controlled integration runs.

## Scope

### In Scope

- Python 3.12 or a compatible supported Python version, with the exact Railway runtime verified during setup.
- Scrapy as the primary HTTP crawling framework.
- Playwright as an optional fallback for pages that require browser execution.
- FastAPI REST API and server-rendered dashboard.
- Jinja2 templates and HTMX for dashboard interactions.
- PostgreSQL as the durable source of truth.
- SQLAlchemy 2 and Alembic for persistence and schema migrations.
- Redis and Celery for background task dispatch/orchestration.
- Pydantic for configuration and request/data validation.
- Pytest for automated testing.
- Docker-based Railway deployment.
- JSON and CSV exports.
- Respectful crawling of publicly accessible pages within applicable site policies and technical access limits.

### Out of Scope for the Initial Release

- Bypassing CAPTCHA, authentication, paywalls, anti-bot protections, or other access controls.
- Circumventing rate limits, robots directives, or explicit site restrictions.
- Scraping private, account-only, or otherwise unauthorized information.
- Guaranteeing 100% of all products or all pages on the website.
- A multi-tenant SaaS product, public customer accounts, billing, or role-based enterprise administration.
- Automatic purchasing, checkout, cart manipulation, or customer account actions.
- Price prediction, product recommendations, or competitor analytics.
- Automatically translating every page at crawl time before the source data is safely persisted.
- Downloading and mirroring all product images into object storage in the first release; initially retain image URLs. Object storage can be added if an explicit need arises.
- Using Firecrawl.
- Assuming the target website uses Magento or any specific CMS before technical inspection confirms it.
- Building a large distributed crawler cluster before a measured need exists.

## Success Criteria

1. Given a valid seed URL on the allowed Audiovideo.lt host, the system creates a durable job and records its seed URL.
2. The crawler can discover and persist category, nested-category, manufacturer, search, pagination, and product URLs when those links are present and accessible in the observed page structure.
3. A product discovered through multiple sources is represented as one canonical product record where identity evidence supports a match, while all source/category relationships remain available.
4. Source Lithuanian text is preserved exactly as extracted, and translation records cannot overwrite it.
5. Missing identifiers or specifications remain null/absent rather than being fabricated.
6. A worker restart does not lose the persisted frontier or mark unprocessed URLs as completed.
7. Every attempted URL has a durable status and a recorded outcome, including parse failures and access restrictions.
8. Coverage reports distinguish discovered, queued, attempted, processed, extracted, incomplete, failed, skipped, and inaccessible states.
9. API clients can list/filter products and categories, inspect a job, and download JSON/CSV exports.
10. An operator can start a crawl, inspect progress, pause/resume/cancel it where supported, and review failures from the dashboard.
11. Automated tests cover parsing, normalization, deduplication, persistence, job recovery, API contracts, and export behavior.
12. Deployment health checks confirm that the web service and worker can connect to PostgreSQL and Redis and that migrations have been applied.

## Operational Success Definition

A crawl is successful only to the extent that its measured work is complete and its records pass validation. A job must not be labelled “complete coverage” merely because its queue is empty. Reports must expose unresolved, failed, inaccessible, and unverified URL populations and explain the denominator used for any percentage.
