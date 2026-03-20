# Connectors

## How tool references work

Plugin files use `~~category` as a placeholder for whatever tool the user
connects in that category. Plugins are tool-agnostic — they describe
workflows in terms of categories rather than specific products.

## Connectors for this plugin

| Category | Placeholder | Purpose | Options |
|----------|-------------|---------|---------|
| Web browser | `~~browser` | Read external analyst feeds — Steno Research X feed, Alpine Macro LinkedIn (Skill 10) | Chrome extension (Claude in Chrome) |

## Notes

Browser access is optional but recommended. Without it:

- Analyst monitoring (Skill 10) will be limited to web search instead of browsing full articles and following links
- All other skills work normally without browser access — ETF data comes from Yahoo Finance via yfinance, not browser scraping

If using browser access, make sure you are logged in to X (for Steno Research feed) and LinkedIn (for Alpine Macro feed) in your Chrome browser. The analyst monitor browses these feeds using your active browser session.
