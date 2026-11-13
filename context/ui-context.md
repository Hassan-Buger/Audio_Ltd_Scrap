# UI Context

## Design Direction

Use a clean, technical operations-dashboard aesthetic. The interface should feel like a reliable data operations console: calm, dense enough for large catalogues, readable during long crawl sessions, and focused on status and data quality rather than decorative effects.

The user has not supplied a preferred brand identity or color palette. The tokens below are a proposed default design system for the first release, not an existing brand specification. Keep all colors centralized so the palette can be changed without rewriting components.

Default to a light theme for long-form tables and product data, with a dark sidebar and restrained blue accent. Do not implement a theme switcher in the first release unless explicitly requested.

## Color Tokens

Define these as CSS custom properties in one shared stylesheet. Components must use tokens, not scattered raw hex values.

| Role | CSS variable | Proposed value |
|---|---|---|
| Main page background | `--color-bg` | `#F5F7FA` |
| Primary surface | `--color-surface` | `#FFFFFF` |
| Subtle surface | `--color-surface-muted` | `#EEF2F6` |
| Sidebar background | `--color-sidebar` | `#17212F` |
| Sidebar hover | `--color-sidebar-hover` | `#243449` |
| Primary text | `--color-text` | `#17212F` |
| Secondary text | `--color-text-muted` | `#64748B` |
| Inverse text | `--color-text-inverse` | `#F8FAFC` |
| Primary accent | `--color-accent` | `#2563EB` |
| Accent hover | `--color-accent-hover` | `#1D4ED8` |
| Border | `--color-border` | `#DCE3EA` |
| Success | `--color-success` | `#15803D` |
| Success background | `--color-success-bg` | `#DCFCE7` |
| Warning | `--color-warning` | `#B45309` |
| Warning background | `--color-warning-bg` | `#FEF3C7` |
| Error | `--color-error` | `#B91C1C` |
| Error background | `--color-error-bg` | `#FEE2E2` |
| Info | `--color-info` | `#0369A1` |
| Info background | `--color-info-bg` | `#E0F2FE` |
| Focus ring | `--color-focus` | `#60A5FA` |

Check text/background contrast before release. Do not rely on color alone to communicate state; pair status colors with labels and/or icons.

## Typography

Use system fonts to avoid an unnecessary font download dependency.

| Role | Font stack | CSS variable |
|---|---|---|
| UI and body | `Inter, ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif` | `--font-sans` |
| IDs, code, technical values | `ui-monospace, SFMono-Regular, Menlo, Consolas, monospace` | `--font-mono` |

Type scale:
- Page title: 1.5rem, weight 650.
- Section title: 1.125rem, weight 600.
- Card title: 0.95rem, weight 600.
- Body: 0.9rem, weight 400.
- Table text: 0.82rem to 0.875rem.
- Metadata/helper text: 0.75rem.
- SKU, EAN, URL fragments and job IDs: monospace, selectable, never truncated without a way to inspect the full value.

## Spacing and Shape

Use a 4px base spacing rhythm.

| Token | Value | Usage |
|---|---:|---|
| `--space-1` | `4px` | icon/text micro gap |
| `--space-2` | `8px` | compact control gap |
| `--space-3` | `12px` | table/card inner spacing |
| `--space-4` | `16px` | standard component spacing |
| `--space-6` | `24px` | section spacing |
| `--space-8` | `32px` | page-level spacing |
| `--radius-sm` | `4px` | compact controls, tags |
| `--radius-md` | `8px` | cards, inputs, buttons |
| `--radius-lg` | `12px` | larger panels and dialogs |
| `--radius-pill` | `999px` | status chips only |

Borders should be subtle and consistent. Avoid excessive shadows; use a small shadow only for floating menus/dialogs where layering needs to be clear.

## Layout Patterns

- **Application shell:** fixed dark left navigation on desktop; main content area scrolls independently where practical.
- **Sidebar:** approximately 232px wide on desktop, collapsible to icon rail if needed. On narrow screens, use a dismissible drawer.
- **Top bar:** page title/breadcrumb on the left; service health and operator controls on the right.
- **Content area:** fluid width with a comfortable maximum reading width for forms and reports; catalogue tables may use the full available width.
- **Dashboard overview:** compact metric cards followed by recent jobs and recent errors.
- **Data tables:** sticky header where helpful, clear sort indicators, server-side pagination, filters above the table, and horizontal overflow on small screens.
- **Job detail:** status summary, progress counters, timeline/log view, and action controls. Always show whether counts are exact or estimated.
- **Product detail:** source and translation sections side by side on wide screens and stacked on narrow screens; specifications in a readable key/value table.
- **Category tree:** expandable nested navigation with counts labelled as crawler-observed or source-reported.
- **Forms:** labels above inputs, helper text below, visible validation errors, and explicit confirmation for cancel/retry operations when needed.
- **Empty states:** explain what is empty and provide one relevant next action.
- **Error states:** explain the failure in plain language and provide a safe retry or diagnostic path when available.

## Components

Use semantic HTML and server-rendered Jinja2 templates. HTMX may progressively enhance forms, filters, and partial refreshes. Do not add React, Vue, or another SPA framework for the first release.

Create shared template partials for:
- navigation and top bar
- metric cards
- status labels
- pagination
- filter bars
- confirmation dialogs
- form controls and validation messages
- flash/notification messages
- table empty/loading/error states

All scraped content is untrusted. Escape it by default; do not mark scraped descriptions as safe HTML without a sanitization policy.

## Status Language

Use consistent lifecycle labels:
- Queued
- In progress
- Paused
- Completed
- Completed with issues
- Failed
- Cancel requested
- Cancelled

URL outcomes should distinguish:
- Discovered
- Queued
- In progress
- Processed
- Retryable failure
- Terminal failure
- Skipped
- Inaccessible

Do not use “100% complete” unless the denominator is explicit and all members of that defined population meet the completion condition.

## Icons

Use Lucide icons through a lightweight server-compatible icon approach or inline SVG assets. Keep icon style consistent and stroke-based.

- Inline with text: 16px.
- Standard navigation/action: 18px.
- Large empty-state illustration/icon: 28–32px.
- Always provide accessible text labels or `aria-label` for icon-only controls.

## Responsive Behavior and Accessibility

- Support desktop, tablet, and mobile layouts.
- Ensure keyboard navigation and visible focus indicators.
- Use semantic headings, labels, tables, and buttons.
- Do not communicate status using color alone.
- Keep interactive targets comfortably sized on touch devices.
- Respect reduced-motion preferences; avoid decorative animation.
- Preserve table access on small screens with overflow or a deliberate card alternative.
