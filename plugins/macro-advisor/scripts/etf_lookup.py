#!/usr/bin/env python3
"""
ETF Lookup — Dynamic thematic ETF discovery via Yahoo Finance.

Two-layer search:
  Layer 1: Keyword match against a curated universe of ~160 liquid ETFs
  Layer 2: Live Yahoo Finance search API for broader discovery (fallback)

All results are verified with real price data before being returned.
Never recommends a ticker that failed price verification.

Guardrails:
  - verification_warnings: tickers that were found but failed price data check
  - unverified_tickers: any ticker from Yahoo search that couldn't be confirmed as real

Usage:
    python etf_lookup.py --theme "euro currency long"
    python etf_lookup.py --theme "volatility hedge"
    python etf_lookup.py --theme "drone warfare defense"
    python etf_lookup.py --verify "FXE,UUP,ARKQ"
    python etf_lookup.py --theme "space satellite defense" --top 5
"""

import argparse
import json
import sys
from datetime import datetime, timedelta


# ═══════════════════════════════════════════════════════════════
# CURATED ETF UNIVERSE (~160 tickers)
# Layer 1 search matches keywords against this dict.
# Organized by asset class for maintainability.
# ═══════════════════════════════════════════════════════════════

ETF_UNIVERSE = {
    # ── Currency / FX ──────────────────────────────────────────
    "FXE": "CurrencyShares Euro Trust",
    "FXY": "CurrencyShares Japanese Yen Trust",
    "FXF": "CurrencyShares Swiss Franc Trust",
    "FXB": "CurrencyShares British Pound Trust",
    "FXA": "CurrencyShares Australian Dollar Trust",
    "FXC": "CurrencyShares Canadian Dollar Trust",
    "CYB": "WisdomTree Chinese Yuan Strategy Fund",
    "CEW": "WisdomTree Emerging Currency Strategy Fund",
    "UUP": "Invesco DB US Dollar Index Bullish Fund",
    "UDN": "Invesco DB US Dollar Index Bearish Fund",

    # ── Volatility ─────────────────────────────────────────────
    "VIXY": "ProShares VIX Short-Term Futures ETF",
    "VIXM": "ProShares VIX Mid-Term Futures ETF",
    "SVXY": "ProShares Short VIX Short-Term Futures ETF",
    "TAIL": "Cambria Tail Risk ETF",

    # ── Fixed Income — Precision ───────────────────────────────
    "SHY": "iShares 1-3 Year Treasury Bond ETF",
    "IEI": "iShares 3-7 Year Treasury Bond ETF",
    "IEF": "iShares 7-10 Year Treasury Bond ETF",
    "TLH": "iShares 10-20 Year Treasury Bond ETF",
    "TLT": "iShares 20+ Year Treasury Bond ETF",
    "VGLT": "Vanguard Long-Term Treasury ETF",
    "SHV": "iShares Short Treasury Bond ETF",
    "BIL": "SPDR Bloomberg 1-3 Month T-Bill ETF",
    "SGOV": "iShares 0-3 Month Treasury Bond ETF",
    "FLOT": "iShares Floating Rate Bond ETF",
    "USFR": "WisdomTree Floating Rate Treasury Fund",
    "STIP": "iShares 0-5 Year TIPS Bond ETF",
    "TIP": "iShares TIPS Bond ETF",
    "SCHP": "Schwab US TIPS ETF",
    "AGG": "iShares Core US Aggregate Bond ETF",
    "BND": "Vanguard Total Bond Market ETF",
    "HYG": "iShares iBoxx High Yield Corporate Bond ETF",
    "JNK": "SPDR Bloomberg High Yield Bond ETF",
    "LQD": "iShares iBoxx Investment Grade Corporate Bond ETF",
    "VCIT": "Vanguard Intermediate-Term Corporate Bond ETF",
    "EMB": "iShares JP Morgan USD Emerging Markets Bond ETF",
    "VWOB": "Vanguard Emerging Markets Government Bond ETF",

    # ── Broad Equity ───────────────────────────────────────────
    "SPY": "SPDR S&P 500 ETF",
    "VOO": "Vanguard S&P 500 ETF",
    "IVV": "iShares Core S&P 500 ETF",
    "QQQ": "Invesco QQQ Nasdaq 100 Trust",
    "IWM": "iShares Russell 2000 Small Cap ETF",
    "VB": "Vanguard Small-Cap ETF",
    "VTV": "Vanguard Value ETF",
    "VUG": "Vanguard Growth ETF",
    "EFA": "iShares MSCI EAFE International Developed ETF",
    "VEA": "Vanguard FTSE Developed Markets ETF",
    "IEFA": "iShares Core MSCI EAFE ETF",
    "EEM": "iShares MSCI Emerging Markets ETF",
    "VWO": "Vanguard FTSE Emerging Markets ETF",
    "IEMG": "iShares Core MSCI Emerging Markets ETF",

    # ── Country / Region ───────────────────────────────────────
    "FXI": "iShares China Large-Cap ETF",
    "KWEB": "KraneShares CSI China Internet ETF",
    "MCHI": "iShares MSCI China ETF",
    "EWJ": "iShares MSCI Japan ETF",
    "DXJ": "WisdomTree Japan Hedged Equity Fund",
    "EWG": "iShares MSCI Germany ETF",
    "EWZ": "iShares MSCI Brazil ETF",
    "INDA": "iShares MSCI India ETF",
    "VGK": "Vanguard FTSE Europe ETF",
    "EZU": "iShares MSCI Eurozone ETF",
    "EWU": "iShares MSCI United Kingdom ETF",
    "EWY": "iShares MSCI South Korea ETF",
    "EWT": "iShares MSCI Taiwan ETF",
    "THD": "iShares MSCI Thailand ETF",
    "EIDO": "iShares MSCI Indonesia ETF",

    # ── Sectors ────────────────────────────────────────────────
    "XLE": "Energy Select Sector SPDR Fund",
    "VDE": "Vanguard Energy ETF",
    "XOP": "SPDR S&P Oil & Gas Exploration & Production ETF",
    "OIH": "VanEck Oil Services ETF",
    "XLF": "Financial Select Sector SPDR Fund",
    "KBE": "SPDR S&P Bank ETF",
    "KRE": "SPDR S&P Regional Banking ETF",
    "IAI": "iShares US Broker-Dealers & Securities Exchanges ETF",
    "XLK": "Technology Select Sector SPDR Fund",
    "VGT": "Vanguard Information Technology ETF",
    "XLV": "Health Care Select Sector SPDR Fund",
    "XBI": "SPDR S&P Biotech ETF",
    "IBB": "iShares Biotech ETF",
    "ARKG": "ARK Genomic Revolution ETF",
    "XHE": "SPDR S&P Health Care Equipment ETF",
    "XLU": "Utilities Select Sector SPDR Fund",
    "XLP": "Consumer Staples Select Sector SPDR Fund",
    "XLY": "Consumer Discretionary Select Sector SPDR Fund",
    "XLRE": "Real Estate Select Sector SPDR Fund",
    "XLI": "Industrial Select Sector SPDR Fund",
    "XLB": "Materials Select Sector SPDR Fund",

    # ── Thematic ───────────────────────────────────────────────
    "ITA": "iShares US Aerospace & Defense ETF",
    "PPA": "Invesco Aerospace & Defense ETF",
    "DFEN": "Direxion Daily Aerospace & Defense Bull 3X ETF",
    "XAR": "SPDR S&P Aerospace & Defense ETF",
    "ARKQ": "ARK Autonomous Technology & Robotics ETF",
    "ROBT": "First Trust Robotics & AI ETF",
    "BOTZ": "Global X Robotics & Artificial Intelligence ETF",
    "IRBO": "iShares Robotics and AI Multisector ETF",
    "CIBR": "First Trust NASDAQ Cybersecurity ETF",
    "HACK": "ETFMG Prime Cyber Security ETF",
    "BUG": "Global X Cybersecurity ETF",
    "SMH": "VanEck Semiconductor ETF",
    "SOXX": "iShares Semiconductor ETF",
    "PSI": "Invesco Semiconductors ETF",
    "ARKK": "ARK Innovation ETF",
    "ARKW": "ARK Next Generation Internet ETF",
    "PAVE": "Global X US Infrastructure Development ETF",
    "IFRA": "iShares US Infrastructure ETF",
    "UFO": "Procure Space ETF",
    "ARKX": "ARK Space Exploration & Innovation ETF",
    "DTCR": "Global X Data Center & Digital Infrastructure ETF",

    # ── Commodities & Mining ───────────────────────────────────
    "GLD": "SPDR Gold Shares",
    "IAU": "iShares Gold Trust",
    "SLV": "iShares Silver Trust",
    "COPX": "Global X Copper Miners ETF",
    "CPER": "United States Copper Index Fund",
    "PICK": "iShares MSCI Global Metals & Mining Producers ETF",
    "LIT": "Global X Lithium & Battery Tech ETF",
    "REMX": "VanEck Rare Earth/Strategic Metals ETF",
    "USO": "United States Oil Fund",
    "BNO": "United States Brent Oil Fund",
    "UNG": "United States Natural Gas Fund",
    "BOIL": "ProShares Ultra Bloomberg Natural Gas ETF",
    "DBA": "Invesco DB Agriculture Fund",
    "WEAT": "Teucrium Wheat Fund",
    "CORN": "Teucrium Corn Fund",
    "DJP": "iPath Bloomberg Commodity Index ETN",
    "GSG": "iShares S&P GSCI Commodity-Indexed Trust",
    "KRBN": "KraneShares Global Carbon Strategy ETF",

    # ── Clean Energy & Nuclear ─────────────────────────────────
    "ICLN": "iShares Global Clean Energy ETF",
    "TAN": "Invesco Solar ETF",
    "FAN": "First Trust Global Wind Energy ETF",
    "URA": "Global X Uranium ETF",
    "URNM": "Sprott Uranium Miners ETF",
    "NLR": "VanEck Uranium+Nuclear Energy ETF",

    # ── Real Estate ────────────────────────────────────────────
    "VNQ": "Vanguard Real Estate ETF",
    "SCHH": "Schwab US REIT ETF",

    # ── Crypto ─────────────────────────────────────────────────
    "BITO": "ProShares Bitcoin Strategy ETF",
    "IBIT": "iShares Bitcoin Trust ETF",
    "ETHE": "Grayscale Ethereum Trust",
    "BLOK": "Amplify Transformational Data Sharing ETF",

    # ── Water ──────────────────────────────────────────────────
    "PHO": "Invesco Water Resources ETF",
    "CGW": "Invesco S&P Global Water Index ETF",

    # ── Cannabis ───────────────────────────────────────────────
    "MSOS": "AdvisorShares Pure US Cannabis ETF",

    # ── MLPs / Pipelines ───────────────────────────────────────
    "AMLP": "Alerian MLP ETF",
}

# Synonym map: common search terms → additional keywords to match
# This helps when the user searches "euro" but the ETF name says "Euro Trust"
KEYWORD_SYNONYMS = {
    "euro": ["eur", "eurozone", "europe"],
    "yen": ["japan", "japanese"],
    "dollar": ["usd", "us dollar"],
    "fx": ["currency", "currencyshares"],
    "currency": ["currencyshares", "fx"],
    "vol": ["volatility", "vix"],
    "volatility": ["vix", "vol"],
    "vix": ["volatility", "vol"],
    "bond": ["treasury", "fixed income", "duration"],
    "rate": ["treasury", "bond", "yield"],
    "rates": ["treasury", "bond", "yield"],
    "duration": ["treasury", "bond", "year"],
    "oil": ["crude", "brent", "petroleum", "energy"],
    "gas": ["natural gas"],
    "gold": ["precious metal", "bullion"],
    "copper": ["mining", "metal"],
    "bitcoin": ["btc", "crypto"],
    "crypto": ["bitcoin", "blockchain"],
    "defense": ["defence", "aerospace", "military"],
    "ai": ["artificial intelligence", "robotics"],
    "semiconductor": ["chip", "chips"],
    "china": ["chinese", "yuan"],
    "india": ["indian"],
    "brazil": ["brazilian"],
    "emerging": ["em", "developing"],
    "long": [],   # directional hints — not keywords for ETF names
    "short": [],
    "bull": ["bullish"],
    "bear": ["bearish"],
}


def search_etfs_by_theme(theme, top_n=5):
    """Two-layer ETF search: curated universe first, Yahoo Finance fallback.

    Returns verified results with guardrail warnings.
    """
    try:
        import yfinance as yf
    except ImportError:
        return {"error": "yfinance not installed. Run: pip install yfinance"}

    raw_keywords = theme.lower().split()

    # Expand keywords using synonym map
    keywords = set(raw_keywords)
    for kw in raw_keywords:
        if kw in KEYWORD_SYNONYMS:
            keywords.update(KEYWORD_SYNONYMS[kw])
    keywords = list(keywords)

    # ── Layer 1: Curated universe keyword match ─────────────
    scored = []
    for ticker, name in ETF_UNIVERSE.items():
        name_lower = name.lower()
        ticker_lower = ticker.lower()

        score = 0
        for kw in keywords:
            if kw in name_lower:
                score += 1
            if kw in ticker_lower:
                score += 1

        # Boost for exact theme substring match
        if theme.lower() in name_lower:
            score += 3
        # Boost for multiple keyword hits
        if score > 1:
            score += 1
        if score > 0:
            scored.append((ticker, name, score))

    scored.sort(key=lambda x: x[2], reverse=True)

    # ── Layer 2: Yahoo Finance live search (if Layer 1 found < top_n) ──
    yahoo_candidates = []
    used_layer2 = False
    if len(scored) < top_n:
        used_layer2 = True
        yahoo_candidates = _yahoo_search(theme, exclude=set(ETF_UNIVERSE.keys()))

    # ── Verify all candidates with real price data ──────────
    verified = []
    verification_warnings = []

    # First verify Layer 1 hits
    for ticker, name, score in scored[:top_n * 2]:
        if len(verified) >= top_n:
            break
        info = verify_etf(ticker)
        if info and not info.get("error"):
            info["match_score"] = score
            info["match_name"] = name
            info["source"] = "curated_universe"
            verified.append(info)
        else:
            verification_warnings.append({
                "ticker": ticker,
                "reason": info.get("error", "unknown") if info else "verification failed",
            })

    # Then verify Layer 2 hits if we still need more
    for ticker, name in yahoo_candidates:
        if len(verified) >= top_n:
            break
        # Skip if already checked
        if any(v["ticker"] == ticker for v in verified):
            continue
        if any(w["ticker"] == ticker for w in verification_warnings):
            continue

        info = verify_etf(ticker)
        if info and not info.get("error"):
            info["match_score"] = 0
            info["match_name"] = name
            info["source"] = "yahoo_search"
            verified.append(info)
        else:
            verification_warnings.append({
                "ticker": ticker,
                "reason": info.get("error", "unknown") if info else "verification failed",
                "source": "yahoo_search",
            })

    result = {
        "theme": theme,
        "search_date": datetime.now().strftime("%Y-%m-%d"),
        "matches": verified,
        "total_candidates_scanned": len(ETF_UNIVERSE),
        "keyword_matches_found": len(scored),
        "used_yahoo_search": used_layer2,
        "yahoo_candidates_found": len(yahoo_candidates),
    }

    if verification_warnings:
        result["verification_warnings"] = verification_warnings

    return result


def _yahoo_search(theme, exclude=None, max_results=10):
    """Layer 2: Use Yahoo Finance search API to discover ETFs not in our curated list.

    Returns list of (ticker, name) tuples. Does NOT verify price data — that
    happens in the caller.
    """
    exclude = exclude or set()
    candidates = []

    try:
        import yfinance as yf

        # yfinance doesn't have a direct search API, but we can use the
        # underlying Yahoo Finance search endpoint
        import urllib.request
        import urllib.parse

        # Try multiple search queries for broader coverage
        queries = [theme]
        # Also try "ETF" appended to narrow results
        if "etf" not in theme.lower():
            queries.append(f"{theme} ETF")

        seen_tickers = set()

        for query in queries:
            try:
                encoded = urllib.parse.quote(query)
                url = f"https://query2.finance.yahoo.com/v1/finance/search?q={encoded}&quotesCount={max_results}&newsCount=0&enableFuzzyQuery=false&quotesQueryId=tss_match_phrase_query"

                req = urllib.request.Request(url, headers={
                    "User-Agent": "Mozilla/5.0 (compatible; MacroAdvisor/1.0)"
                })
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read().decode("utf-8"))

                for quote in data.get("quotes", []):
                    ticker = quote.get("symbol", "")
                    name = quote.get("longname") or quote.get("shortname") or ""
                    qtype = quote.get("quoteType", "")
                    exchange = quote.get("exchange", "")

                    # Filter: only ETFs on major exchanges
                    if qtype != "ETF":
                        continue
                    if ticker in exclude or ticker in seen_tickers:
                        continue
                    # Skip non-US exchanges (we want USD-listed)
                    if exchange not in ("NYQ", "PCX", "NMS", "NGM", "BTS", "ASE", ""):
                        continue

                    seen_tickers.add(ticker)
                    candidates.append((ticker, name))

            except Exception:
                # Yahoo search is best-effort — if it fails, Layer 1 results stand
                continue

    except Exception:
        pass

    return candidates[:max_results]


def verify_etf(ticker):
    """Verify an ETF exists and return key stats.

    This is the hallucination guardrail: no ticker gets recommended without
    verified price data. If price data is missing or stale (>5 days old),
    the ETF is rejected.
    """
    try:
        import yfinance as yf

        etf = yf.Ticker(ticker)

        # Get basic info
        info = etf.info or {}

        # Get recent price data (3 months)
        end = datetime.now()
        start_3m = end - timedelta(days=90)

        hist = etf.history(start=start_3m.strftime("%Y-%m-%d"),
                          end=end.strftime("%Y-%m-%d"))

        if hist is None or len(hist) == 0:
            return {"ticker": ticker, "error": "no price data — ticker may not exist or may be delisted"}

        close = hist["Close"]
        latest_price = float(close.iloc[-1])
        latest_date = close.index[-1]

        # Staleness check: if the last price is more than 5 trading days old,
        # the ETF may be halted, delisted, or illiquid
        days_stale = (datetime.now() - latest_date.to_pydatetime().replace(tzinfo=None)).days
        if days_stale > 7:
            return {"ticker": ticker, "error": f"stale data — last price is {days_stale} days old, may be delisted or illiquid"}

        # Liquidity check: reject if average daily volume is under 10,000
        vol = hist["Volume"].tail(20)
        avg_volume = int(vol.mean()) if len(vol) > 0 else 0
        if avg_volume < 10000:
            return {"ticker": ticker, "error": f"illiquid — avg daily volume {avg_volume:,} (minimum 10,000)"}

        # 1-month change
        month_ago_idx = max(0, len(close) - 22)
        month_ago = float(close.iloc[month_ago_idx])
        month_change = round((latest_price - month_ago) / month_ago * 100, 2) if month_ago != 0 else None

        # 3-month change
        three_month_ago = float(close.iloc[0])
        three_month_change = round((latest_price - three_month_ago) / three_month_ago * 100, 2) if three_month_ago != 0 else None

        result = {
            "ticker": ticker,
            "name": info.get("longName") or info.get("shortName") or ticker,
            "category": info.get("category", "Unknown"),
            "latest_price": round(latest_price, 2),
            "latest_date": latest_date.strftime("%Y-%m-%d"),
            "month_change_pct": month_change,
            "three_month_change_pct": three_month_change,
            "avg_daily_volume": avg_volume,
            "expense_ratio": info.get("annualReportExpenseRatio"),
            "total_assets": info.get("totalAssets"),
            "verified": True,
        }

        # Human-readable AUM
        assets = info.get("totalAssets")
        if assets:
            if assets >= 1e9:
                result["aum_display"] = f"${assets / 1e9:.1f}B"
            elif assets >= 1e6:
                result["aum_display"] = f"${assets / 1e6:.0f}M"
            else:
                result["aum_display"] = f"${assets:,.0f}"

        return result

    except Exception as e:
        return {"ticker": ticker, "error": str(e)[:200]}


def verify_tickers(ticker_string):
    """Verify a comma-separated list of tickers."""
    tickers = [t.strip().upper() for t in ticker_string.split(",")]
    results = []
    for t in tickers:
        info = verify_etf(t)
        results.append(info)
    return {"tickers": results, "verified_date": datetime.now().strftime("%Y-%m-%d")}


def main():
    parser = argparse.ArgumentParser(description="ETF Lookup — Dynamic thematic search with verification")
    parser.add_argument("--theme", help="Search theme (e.g., 'euro currency long', 'volatility hedge')")
    parser.add_argument("--verify", help="Verify comma-separated tickers (e.g., 'FXE,UUP,ARKQ')")
    parser.add_argument("--top", type=int, default=5, help="Number of top results (default: 5)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    args = parser.parse_args()

    if args.verify:
        results = verify_tickers(args.verify)
        if args.json:
            print(json.dumps(results, indent=2, default=str))
        else:
            print(f"ETF Verification — {results['verified_date']}\n")
            for r in results["tickers"]:
                if r.get("error"):
                    print(f"  {r['ticker']}: FAILED — {r['error']}")
                else:
                    aum = r.get("aum_display", "N/A")
                    er = f"{r['expense_ratio']:.2%}" if r.get("expense_ratio") else "N/A"
                    print(f"  {r['ticker']}: ${r['latest_price']} | 1M: {r.get('month_change_pct', 'N/A')}% | 3M: {r.get('three_month_change_pct', 'N/A')}% | AUM: {aum} | ER: {er} | Vol: {r.get('avg_daily_volume', 'N/A'):,}")

    elif args.theme:
        results = search_etfs_by_theme(args.theme, args.top)
        if args.json:
            print(json.dumps(results, indent=2, default=str))
        else:
            print(f"ETF Search: \"{args.theme}\" — {results.get('search_date', 'N/A')}")
            print(f"Layer 1: {results.get('total_candidates_scanned', 0)} curated ETFs scanned, {results.get('keyword_matches_found', 0)} keyword matches")
            if results.get("used_yahoo_search"):
                print(f"Layer 2: Yahoo Finance search triggered, {results.get('yahoo_candidates_found', 0)} additional candidates")
            print()

            if results.get("verification_warnings"):
                for w in results["verification_warnings"]:
                    src = f" [{w.get('source', 'curated')}]" if w.get("source") == "yahoo_search" else ""
                    print(f"  ✗ {w['ticker']}{src}: {w['reason']}")
                print()

            if results["matches"]:
                for i, m in enumerate(results["matches"], 1):
                    aum = m.get("aum_display", "N/A")
                    er = f"{m['expense_ratio']:.2%}" if m.get("expense_ratio") else "N/A"
                    src = " [YAHOO]" if m.get("source") == "yahoo_search" else ""
                    print(f"  {i}. {m['ticker']}{src} — {m.get('name', 'Unknown')}")
                    print(f"     ${m['latest_price']} | 1M: {m.get('month_change_pct', 'N/A')}% | 3M: {m.get('three_month_change_pct', 'N/A')}% | AUM: {aum} | ER: {er} | Vol: {m.get('avg_daily_volume', 'N/A'):,}")
                    print()
            else:
                print("  No verified matches found. The theme may need a different ETF expression approach.")
    else:
        parser.print_help()

    return 0


if __name__ == "__main__":
    sys.exit(main())
