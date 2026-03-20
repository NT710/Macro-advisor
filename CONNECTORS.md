# Connectors

## How tool references work

Plugin files use `~~category` as a placeholder for whatever tool the user
connects in that category. Plugins are tool-agnostic — they describe
workflows in terms of categories rather than specific products.

## Connectors for this plugin

| Category | Placeholder | Purpose | Options |
|----------|-------------|---------|---------|
| Web browser | `~~browser` | Scrape justETF for ETF data, read external analyst feeds (Steno Research X feed, Alpine Macro LinkedIn) | Chrome extension (Claude in Chrome) |

## Notes

Browser access is optional but recommended. Without it:

- ETF mapping during `/setup` and `/update-etfs` will use Yahoo Finance only (less comprehensive than justETF)
- Analyst monitoring (Skill 10) will be limited to web search instead of browsing full articles
- All other skills work normally without browser access
