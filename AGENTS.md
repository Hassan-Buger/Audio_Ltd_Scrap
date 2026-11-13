# Application Building Context

This repository contains a Python scraper and operations dashboard for Audiovideo.lt.

Read the following files in order before implementing code or making architectural decisions:

1. `context/project-overview.md` — product definition, goals, user flow, scope, seed URLs, and success criteria.
2. `context/architecture.md` — approved/proposed stack, service boundaries, data model, persistence, crawling, API, deployment, and invariants.
3. `context/ui-context.md` — dashboard visual direction, design tokens, layout, status language, and accessibility conventions.
4. `context/code-standards.md` — Python, FastAPI, Scrapy, database, task, extraction, testing, and security conventions.
5. `context/ai-workflow-rules.md` — one-unit-at-a-time workflow, missing-requirement handling, protected operations, and verification rules.
6. `context/progress-tracker.md` — current phase, verified progress, open questions, decisions, and next steps.

## Mandatory Rules

- Treat PostgreSQL as the durable source of truth for jobs, URL frontier, and extracted records.
- Preserve Lithuanian source values. Store translations separately.
- Do not invent missing product data or claim unverified site coverage.
- Do not merge distinct product variants without strong identity evidence.
- Do not use Firecrawl.
- Use Scrapy for normal HTTP crawling and Playwright only when verified page behavior requires browser rendering.
- Respect applicable site terms, robots directives, request limits, and access restrictions. Never bypass CAPTCHA, authentication, or anti-bot controls.
- Do not assume the target site's CMS, selectors, or current product counts. Verify them.
- Keep long-running crawl work out of HTTP request handlers.
- Keep all crawling bounded by approved host, depth, URL, concurrency, and rate limits.
- Never commit secrets or real environment files.

Update `context/progress-tracker.md` after every meaningful planning or implementation change. If implementation changes product scope, architecture, storage, invariants, code conventions, or UI design, update the relevant context file before continuing.

Do not mark work complete unless its specification's verification checklist has been run and passed. Report exact commands and outcomes. If repository integration or live-site verification is unavailable, state that clearly rather than implying it was done.
