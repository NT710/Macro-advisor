"""
Design tokens for the Alpine Report design system.

Local copy — duplicated in both macro-advisor and trading-engine plugins
so each plugin is self-contained.
"""

# ---------------------------------------------------------------------------
# CSS custom properties — the full :root block
# ---------------------------------------------------------------------------

CSS_VARIABLES = """\
:root {
    --bg: #0f1117;
    --surface: #1a1d27;
    --surface2: #242836;
    --border: #2e3345;
    --text: #e4e4e7;
    --text-muted: #8b8fa3;
    --accent: #60a5fa;
    --green: #34d399;
    --red: #f87171;
    --yellow: #fbbf24;
    --orange: #fb923c;
    --regime-goldilocks: #34d399;
    --regime-overheating: #fbbf24;
    --regime-stagflation: #f87171;
    --regime-disinflation: #60a5fa;
    --regime-goldilocks-bg: #34d39915;
    --regime-overheating-bg: #fbbf2415;
    --regime-stagflation-bg: #f8717115;
    --regime-disinflation-bg: #60a5fa15;
    --text-xs: 11px;
    --text-sm: 13px;
    --text-base: 15px;
    --text-lg: 18px;
    --text-xl: 24px;
    --text-2xl: 36px;
    --font-mono: 'SF Mono', 'Fira Code', monospace;
    --space-1: 4px;
    --space-2: 8px;
    --space-3: 12px;
    --space-4: 16px;
    --space-6: 24px;
    --space-8: 32px;
    --space-12: 48px;
    --space-16: 64px;
    --shadow-1: 0 1px 3px rgba(0,0,0,.3);
    --shadow-2: 0 4px 12px rgba(0,0,0,.4);
    --shadow-3: 0 8px 24px rgba(0,0,0,.5);
}"""

# ---------------------------------------------------------------------------
# Regime colors — used by SVG generators
# ---------------------------------------------------------------------------

REGIME_COLORS = {
    "Goldilocks": "#34d399",
    "Overheating": "#fbbf24",
    "Stagflation": "#f87171",
    "Disinflationary Slowdown": "#60a5fa",
    "Unknown": "#8b8fa3",
}

REGIME_COLORS_BG = {
    "Goldilocks": "#34d39915",
    "Overheating": "#fbbf2415",
    "Stagflation": "#f8717115",
    "Disinflationary Slowdown": "#60a5fa15",
    "Unknown": "#8b8fa315",
}

# ---------------------------------------------------------------------------
# @font-face declaration template for Inter (base64 inlined by generators)
# ---------------------------------------------------------------------------

FONT_FACE_CSS = """\
@font-face {{
    font-family: 'Inter';
    font-style: normal;
    font-weight: 100 900;
    font-display: swap;
    src: url('{data_uri}') format('woff2');
}}"""
