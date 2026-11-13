# AI Workflow Rules

## Required Approach

Build this project incrementally using the context files and approved unit specifications as the source of truth. Do not begin implementation from a broad request alone. Before coding, read all six context files in the order specified by `AGENTS.md`. If a unit specification exists, read it fully and implement only that unit.

Use a disciplined Implement → Correct → Close cycle for each unit:
1. **Implement:** implement the unit exactly within its scope and update the progress tracker.
2. **Correct:** fix only verified mismatches between implementation and specification; do not expand scope.
3. **Close:** run the required verification, record results, update progress, and mark the unit complete only when all required checks pass.

## One Unit at a Time

- Work on one independently verifiable unit at a time.
- Do not implement multiple unrelated system boundaries in one unit.
- Complete dependencies before dependent units.
- Keep backend contracts stable before wiring the dashboard to real data.
- Build UI shells with clearly labelled placeholder states before connecting live data when the plan calls for that sequence.
- Do not add speculative features, dependencies, services, or abstractions.
- Do not start a later unit because it appears easy while the current unit remains unverified.

## Scope Boundaries

- Keep each unit small enough to review and test in one focused implementation cycle.
- Split work when it mixes database schema, crawler behavior, API contracts, and dashboard interaction without a single independently verifiable outcome.
- Do not combine target-site reconnaissance with assumptions about final selectors. First inspect actual page responses and document observed structures.
- Do not build Playwright flows until a real page has been shown to require browser rendering.
- Do not build translation automation until source extraction and persistence are stable.
- Do not add image downloading or object storage unless explicitly approved.
- Do not introduce Firecrawl.

## Handling Missing or Ambiguous Requirements

- Do not invent product behavior, target-site selectors, category counts, product counts, URL patterns, or CMS identity.
- If the requirement is missing or ambiguous, stop the affected implementation path and add a precise item to `context/progress-tracker.md` under **Open Questions**.
- If the ambiguity affects a single unit but a safe default is possible, state the assumption in that unit's specification and make it easy to change.
- Ask the user only for decisions that cannot be resolved safely from existing context.
- Do not silently broaden the scope to “all pages” without defining host limits, URL patterns, crawl limits, and access policy.
- Do not represent indexed search snippets or stale page counts as live verified site totals.
- If actual repository files are not available, do not claim to have inspected or modified a repository. Generate repository-ready files and clearly mark integration as pending.

## Target-Site Reconnaissance Rules

- Inspect live public pages and their actual HTTP responses where access permits.
- Record observation date, URL, page type, status, relevant headers, pagination behavior, and DOM evidence.
- Treat the four seed URLs in `project-overview.md` as entry points only.
- Confirm category tree, manufacturer page behavior, search results, pagination, canonical URL rules, product detail structure, and any JavaScript dependency before writing selectors.
- Save sanitized representative HTML fixtures where legally and operationally appropriate.
- Respect applicable terms, robots directives, access restrictions, and reasonable request rates.
- Never bypass CAPTCHA, login, anti-bot challenges, or explicit restrictions.
- If blocked or inaccessible, record the limitation and stop that path; do not attempt circumvention.

## Data Integrity Rules

- Preserve original Lithuanian source values.
- Keep English translations separate and traceable.
- Never translate or alter identifiers, model numbers, technical codes, numeric values, or units.
- Keep raw and normalized values when normalization can change meaning or formatting.
- Do not merge products solely by similar title or image.
- Preserve product variants unless strong identity evidence supports a match.
- Keep every discovered category/source relationship even when products are deduplicated.
- Do not fabricate missing values or silently substitute inferred data.
- Keep URL and product provenance so results can be traced to a source page and crawl run.

## Reliability Rules

- PostgreSQL must remain the authoritative durable store for jobs and URL frontier.
- Redis must never be the only record of pending or completed work.
- Make crawl processing idempotent and safe under duplicate task delivery.
- Persist URL state transitions and extraction outcomes.
- Use bounded retries and classify retryable versus terminal failures.
- Recover abandoned URL claims after worker crashes/redeployments.
- Do not mark a URL complete until its outcome has been committed.
- Keep crawling bounded by host, depth, page count, request rate, and configured scope.
- Use Playwright only as a fallback, not as the default for every page.

## Protected Files and Operations

Do not perform any of the following without explicit instruction or an approved specification:
- Delete production data or truncate catalogue tables.
- Run destructive database migrations or reset a production database.
- Change production credentials, authentication configuration, or Railway service settings.
- Increase crawl concurrency or remove rate limits beyond the approved policy.
- Add a new external paid service or translation provider.
- Download all product images or introduce object storage.
- Change canonical product identity rules in a way that could merge or split existing records.
- Change the target host allowlist or relax SSRF protections.
- Remove tests, lint rules, validation, or coverage reporting to make a build pass.
- Commit secrets, cookies, session tokens, or real environment files.

## Documentation Synchronization

Update the relevant context file whenever implementation changes:
- product goals, scope, or acceptance criteria → `project-overview.md`
- stack, boundaries, schema, storage, deployment, auth, or invariants → `architecture.md`
- coding patterns, validation, testing, or file conventions → `code-standards.md`
- agent workflow or protected operations → `ai-workflow-rules.md`
- dashboard theme, tokens, layout, or component conventions → `ui-context.md`
- implementation status, unresolved questions, and next steps → `progress-tracker.md`

Do not make an architecture change only in code. Record the decision and rationale in the context files and progress tracker.

## Verification Before Closing a Unit

1. All acceptance criteria in the unit specification are checked.
2. Relevant unit and integration tests pass.
3. Linting/type checks pass if configured for the project.
4. Database migrations apply cleanly where relevant.
5. No architecture invariant has been violated.
6. Failure paths and missing-data behavior are tested where relevant.
7. Logs do not expose secrets or sensitive request headers.
8. `context/progress-tracker.md` reflects the real state and records test commands/results.
9. Any changed architecture, scope, or standards are reflected in the relevant context file.
10. The agent reports what changed, what was verified, what failed, and what remains open.

Do not mark a unit complete when verification is skipped or failing. Record the exact reason and leave it In Progress or Blocked.
