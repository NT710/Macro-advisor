# Connectors

## How tool references work

Plugin files use `~~category` as a placeholder for whatever tool the user
connects in that category. Plugins are tool-agnostic — they describe
workflows in terms of categories rather than specific products.

## Connectors for this plugin

None required. The trading engine communicates with Alpaca via the alpaca-py SDK directly through Python scripts. No browser or external tool connectors needed.

## Dependencies

This plugin depends on the **Macro Advisor** plugin's outputs. The Macro Advisor must be installed and running its weekly cycle for the trading engine to have signals to act on. The trading engine reads macro advisor outputs — it never writes to or modifies them.
