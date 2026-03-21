# Connectors

## How tool references work

Plugin files use `~~category` as a placeholder for whatever tool the user
connects in that category. Plugins are tool-agnostic — they describe
workflows in terms of categories rather than specific products.

## Connectors for this plugin

| Category | Placeholder | Purpose | Options |
|----------|-------------|---------|---------|
| Web browser | `~~browser` | Browse analyst feeds on X (Steno, Gromen) and LinkedIn (Alpine Macro) for Skill 10 | Chrome extension (Claude in Chrome) |

## Notes

Skill 10 monitors 8 external analysts. Three require browser access (X and LinkedIn), five use WebFetch:

- **Browser (Chrome):** Andreas Steno (X), Luke Gromen (X), Alpine Macro (LinkedIn)
- **WebFetch:** Alfonso Peccatiello/Macro Compass (Substack), MacroVoices (podcast transcripts), Howard Marks/Oaktree (memos), Lyn Alden (monthly newsletter), Evergreen Gavekal (blog)

Browser access is optional. Without it, X and LinkedIn sources fall back to web search instead of full article browsing. All other analysts and all non-analyst skills work normally without browser access.

If using browser access, make sure you are logged in to X and LinkedIn in your Chrome browser.
