#!/usr/bin/env python3
"""
ETF Lookup — Dynamic thematic ETF discovery via Yahoo Finance.

Called by the thesis generator when it needs ETF exposure for a theme
not covered by the static reference table in RULES.md.

Usage:
    python etf_lookup.py --theme "drone warfare defense"
    python etf_lookup.py --theme "nuclear energy uranium"
    python etf_lookup.py --verify "ARKQ,ITA,DFEN"
    python etf_lookup.py --theme "space satellite defense" --top 5
"""

import argparse
import json
import sys
from datetime import datetime, timedelta


def search_etfs_by_theme(theme, top_n=5):
    """Search Yahoo Finance for ETFs matching a theme."""
    try:
        import yfinance as yf
    except ImportError:
        return {"error": "yfinance not installed"}

    # Build search keywords from the theme
    keywords = theme.lower().split()

    # Known ETF universe to scan — broader set than the reference table
    # This is a curated list of liquid, well-known thematic/sector ETFs
    ETF_UNIVERSE = {
        # Defense & Aerospace
        "ITA": "iShares US Aerospace & Defense",
        "PPA": "Invesco Aerospace & Defense",
        "DFEN": "Direxion Daily Aerospace & Defense Bull 3X",
        "XAR": "SPDR S&P Aerospace & Defense",
        # Robotics, AI, Drones
        "ARKQ": "ARK Autonomous Technology & Robotics",
        "ROBT": "First Trust Robotics & AI",
        "BOTZ": "Global X Robotics & AI",
        "IRBO": "iShares Robotics and AI Multisector",
        # Cybersecurity
        "CIBR": "First Trust NASDAQ Cybersecurity",
        "HACK": "ETFMG Prime Cyber Security",
        "BUG": "Global X Cybersecurity",
        # Semiconductors
        "SMH": "VanEck Semiconductor",
        "SOXX": "iShares Semiconductor",
        "PSI": "Invesco Semiconductors",
        # Energy
        "XLE": "Energy Select Sector SPDR",
        "VDE": "Vanguard Energy",
        "XOP": "SPDR S&P Oil & Gas Exploration",
        "OIH": "VanEck Oil Services",
        "USO": "United States Oil Fund",
        "BNO": "United States Brent Oil Fund",
        "AMLP": "Alerian MLP",
        # Clean Energy & Nuclear
        "ICLN": "iShares Global Clean Energy",
        "TAN": "Invesco Solar",
        "FAN": "First Trust Global Wind Energy",
        "URA": "Global X Uranium",
        "URNM": "Sprott Uranium Miners",
        "NLR": "VanEck Uranium+Nuclear Energy",
        # Space
        "UFO": "Procure Space",
        "ARKX": "ARK Space Exploration & Innovation",
        # Biotech & Healthcare
        "XBI": "SPDR S&P Biotech",
        "IBB": "iShares Biotech",
        "XLV": "Health Care Select Sector SPDR",
        "ARKG": "ARK Genomic Revolution",
        "XHE": "SPDR S&P Health Care Equipment",
        # Financials
        "XLF": "Financial Select Sector SPDR",
        "KBE": "SPDR S&P Bank",
        "KRE": "SPDR S&P Regional Banking",
        "IAI": "iShares US Broker-Dealers & Securities Exchanges",
        # Technology
        "XLK": "Technology Select Sector SPDR",
        "VGT": "Vanguard Information Technology",
        "ARKK": "ARK Innovation",
        "ARKW": "ARK Next Generation Internet",
        # Infrastructure
        "PAVE": "Global X US Infrastructure Development",
        "IFRA": "iShares US Infrastructure",
        # Commodities & Mining
        "GLD": "SPDR Gold Shares",
        "IAU": "iShares Gold Trust",
        "SLV": "iShares Silver Trust",
        "COPX": "Global X Copper Miners",
        "PICK": "iShares MSCI Global Metals & Mining",
        "LIT": "Global X Lithium & Battery Tech",
        "DBA": "Invesco DB Agriculture",
        "DJP": "iPath Bloomberg Commodity",
        "GSG": "iShares S&P GSCI Commodity",
        "REMX": "VanEck Rare Earth/Strategic Metals",
        # Country/Region
        "FXI": "iShares China Large-Cap",
        "KWEB": "KraneShares CSI China Internet",
        "MCHI": "iShares MSCI China",
        "EWJ": "iShares MSCI Japan",
        "DXJ": "WisdomTree Japan Hedged Equity",
        "EWG": "iShares MSCI Germany",
        "EWZ": "iShares MSCI Brazil",
        "INDA": "iShares MSCI India",
        "VGK": "Vanguard FTSE Europe",
        "EZU": "iShares MSCI Eurozone",
        "EEM": "iShares MSCI Emerging Markets",
        "VWO": "Vanguard FTSE Emerging Markets",
        "EFA": "iShares MSCI EAFE",
        # Real Estate
        "VNQ": "Vanguard Real Estate",
        "SCHH": "Schwab US REIT",
        "XLRE": "Real Estate Select Sector SPDR",
        # Utilities & Defensives
        "XLU": "Utilities Select Sector SPDR",
        "XLP": "Consumer Staples Select Sector SPDR",
        "XLY": "Consumer Discretionary Select Sector SPDR",
        # Fixed Income
        "TLT": "iShares 20+ Year Treasury",
        "SHV": "iShares Short Treasury",
        "BIL": "SPDR Bloomberg 1-3 Month T-Bill",
        "SGOV": "iShares 0-3 Month Treasury",
        "HYG": "iShares iBoxx High Yield Corporate",
        "JNK": "SPDR Bloomberg High Yield",
        "LQD": "iShares iBoxx Investment Grade Corporate",
        "TIP": "iShares TIPS Bond",
        "EMB": "iShares JP Morgan USD EM Bond",
        # Water
        "PHO": "Invesco Water Resources",
        "CGW": "Invesco S&P Global Water Index",
        # Cannabis
        "MSOS": "AdvisorShares Pure US Cannabis",
        # Blockchain/Crypto adjacent
        "BITO": "ProShares Bitcoin Strategy",
        "BLOK": "Amplify Transformational Data Sharing",
        # Broad Market
        "SPY": "SPDR S&P 500",
        "QQQ": "Invesco QQQ Trust",
        "IWM": "iShares Russell 2000",
        "VTV": "Vanguard Value",
        "VUG": "Vanguard Growth",
        "VOO": "Vanguard S&P 500",
    }

    # Score each ETF by keyword match against its name
    scored = []
    for ticker, name in ETF_UNIVERSE.items():
        name_lower = name.lower()
        score = sum(1 for kw in keywords if kw in name_lower or kw in ticker.lower())
        # Boost for exact substring match
        if theme.lower() in name_lower:
            score += 3
        # Boost for multiple keyword hits
        if score > 1:
            score += 1
        if score > 0:
            scored.append((ticker, name, score))

    # Sort by score descending
    scored.sort(key=lambda x: x[2], reverse=True)

    if not scored:
        return {"theme": theme, "matches": [], "note": "No ETFs matched. Try broader keywords or verify manually."}

    # Take top N and verify with Yahoo Finance
    candidates = scored[:top_n * 2]  # Fetch extra in case some fail
    verified = []

    for ticker, name, score in candidates:
        if len(verified) >= top_n:
            break
        info = verify_etf(ticker)
        if info and not info.get("error"):
            info["match_score"] = score
            info["match_name"] = name
            verified.append(info)

    return {
        "theme": theme,
        "search_date": datetime.now().strftime("%Y-%m-%d"),
        "matches": verified,
        "total_candidates_scanned": len(ETF_UNIVERSE),
        "keyword_matches_found": len(scored),
    }


def verify_etf(ticker):
    """Verify an ETF exists and return key stats."""
    try:
        import yfinance as yf

        etf = yf.Ticker(ticker)

        # Get basic info
        info = etf.info or {}

        # Get recent price data
        end = datetime.now()
        start_1m = end - timedelta(days=30)
        start_3m = end - timedelta(days=90)

        hist = etf.history(start=start_3m.strftime("%Y-%m-%d"),
                          end=end.strftime("%Y-%m-%d"))

        if hist is None or len(hist) == 0:
            return {"ticker": ticker, "error": "no price data"}

        close = hist["Close"]
        latest_price = float(close.iloc[-1])

        # 1-month change
        month_ago_idx = max(0, len(close) - 22)
        month_ago = float(close.iloc[month_ago_idx])
        month_change = round((latest_price - month_ago) / month_ago * 100, 2) if month_ago != 0 else None

        # 3-month change
        three_month_ago = float(close.iloc[0])
        three_month_change = round((latest_price - three_month_ago) / three_month_ago * 100, 2) if three_month_ago != 0 else None

        # Volume (average daily, last 20 days)
        vol = hist["Volume"].tail(20)
        avg_volume = int(vol.mean()) if len(vol) > 0 else None

        result = {
            "ticker": ticker,
            "name": info.get("longName") or info.get("shortName") or ticker,
            "category": info.get("category", "Unknown"),
            "latest_price": round(latest_price, 2),
            "latest_date": close.index[-1].strftime("%Y-%m-%d"),
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
        return {"ticker": ticker, "error": str(e)[:100]}


def verify_tickers(ticker_string):
    """Verify a comma-separated list of tickers."""
    tickers = [t.strip() for t in ticker_string.split(",")]
    results = []
    for t in tickers:
        info = verify_etf(t)
        results.append(info)
    return {"tickers": results, "verified_date": datetime.now().strftime("%Y-%m-%d")}


def main():
    parser = argparse.ArgumentParser(description="ETF Lookup — Dynamic thematic search")
    parser.add_argument("--theme", help="Search theme (e.g., 'drone warfare defense')")
    parser.add_argument("--verify", help="Verify comma-separated tickers (e.g., 'ARKQ,ITA,DFEN')")
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
                    print(f"  {r['ticker']}: ERROR — {r['error']}")
                else:
                    aum = r.get("aum_display", "N/A")
                    er = f"{r['expense_ratio']:.2%}" if r.get("expense_ratio") else "N/A"
                    print(f"  {r['ticker']}: ${r['latest_price']} | 1M: {r.get('month_change_pct', 'N/A')}% | 3M: {r.get('three_month_change_pct', 'N/A')}% | AUM: {aum} | ER: {er}")

    elif args.theme:
        results = search_etfs_by_theme(args.theme, args.top)
        if args.json:
            print(json.dumps(results, indent=2, default=str))
        else:
            print(f"ETF Search: \"{args.theme}\" — {results.get('search_date', 'N/A')}")
            print(f"Scanned {results.get('total_candidates_scanned', 0)} ETFs, {results.get('keyword_matches_found', 0)} keyword matches\n")
            if results["matches"]:
                for i, m in enumerate(results["matches"], 1):
                    aum = m.get("aum_display", "N/A")
                    er = f"{m['expense_ratio']:.2%}" if m.get("expense_ratio") else "N/A"
                    print(f"  {i}. {m['ticker']} — {m.get('name', 'Unknown')}")
                    print(f"     Price: ${m['latest_price']} | 1M: {m.get('month_change_pct', 'N/A')}% | 3M: {m.get('three_month_change_pct', 'N/A')}% | AUM: {aum} | ER: {er}")
                    print()
            else:
                print("  No verified matches found. Try broader keywords.")
    else:
        parser.print_help()

    return 0


if __name__ == "__main__":
    sys.exit(main())
