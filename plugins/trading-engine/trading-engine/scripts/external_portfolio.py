#!/usr/bin/env python3
"""External Portfolio Utility — pricing, classification, and snapshot management.

This script handles yfinance interactions for the external portfolio overlay (T8).
It prices user holdings, pulls FX rates, classifies assets, and manages snapshots.

Usage:
  # Validate and classify a ticker (used during setup)
  python external_portfolio.py --action classify --ticker "QQQ"

  # Refresh all prices and save snapshot
  python external_portfolio.py --action refresh_prices \
    --config config/external-positions.json \
    --user-config config/user-config.json \
    --output outputs/external/

  # Save dated snapshot for historical tracking
  python external_portfolio.py --action save_snapshot \
    --config config/external-positions.json \
    --user-config config/user-config.json \
    --output outputs/external/
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

try:
    import yfinance as yf
except ImportError:
    print("ERROR: yfinance not installed. Run: pip install yfinance --break-system-packages")
    sys.exit(1)


# ── Classification helpers ────────────────────────────────

def classify_ticker(ticker: str) -> dict:
    """Pull all available metadata from yfinance for a single ticker.

    Returns a classification dict with as much data as yfinance provides.
    The caller decides what to do with missing fields.
    """
    result = {
        "ticker": ticker,
        "valid": False,
        "name": None,
        "quote_type": None,
        "currency": None,
        "exchange": None,
        "current_price": None,
        "classification": {
            "asset_class": None,
            "sector": None,
            "industry": None,
            "geography": None,
            "category": None,  # ETF category like "Large Growth"
        },
        "sector_weightings": None,  # ETF sector breakdown (dict)
        "asset_classes": None,  # ETF stock/bond/other split (dict)
        "top_holdings": None,  # ETF top 10 holdings (list)
        "total_assets": None,  # ETF AUM
        "missing_fields": [],
    }

    try:
        t = yf.Ticker(ticker)
        info = t.info

        if not info or info.get("quoteType") is None:
            result["error"] = f"Ticker '{ticker}' not found on Yahoo Finance"
            return result

        result["valid"] = True
        result["name"] = info.get("shortName") or info.get("longName")
        result["quote_type"] = info.get("quoteType")
        result["currency"] = info.get("currency")
        result["exchange"] = info.get("exchange")

        # Current price
        hist = t.history(period="5d")
        if not hist.empty:
            result["current_price"] = round(float(hist["Close"].iloc[-1]), 4)

        # ── Individual stock classification ──
        if info.get("quoteType") == "EQUITY":
            result["classification"]["asset_class"] = "equities"
            result["classification"]["sector"] = info.get("sector")
            result["classification"]["industry"] = info.get("industry")
            result["classification"]["geography"] = info.get("country")

            if not result["classification"]["sector"]:
                result["missing_fields"].append("sector")
            if not result["classification"]["geography"]:
                result["missing_fields"].append("geography")

        # ── ETF classification ──
        elif info.get("quoteType") == "ETF":
            result["classification"]["category"] = info.get("category")
            result["total_assets"] = info.get("totalAssets")

            # Asset classes (stock/bond/other split)
            try:
                ac = t.funds_data.asset_classes
                if ac:
                    result["asset_classes"] = {k: round(v, 4) for k, v in ac.items() if v > 0}
                    # Derive primary asset class from the split
                    stock_pct = ac.get("stockPosition", 0)
                    bond_pct = ac.get("bondPosition", 0)
                    other_pct = ac.get("otherPosition", 0)

                    if stock_pct > 0.5:
                        result["classification"]["asset_class"] = "equities"
                    elif bond_pct > 0.5:
                        result["classification"]["asset_class"] = "fixed_income"
                    elif other_pct > 0.5:
                        # Distinguish commodities, FX, crypto from category
                        cat = (info.get("category") or "").lower()
                        if "commodit" in cat:
                            result["classification"]["asset_class"] = "commodities"
                        elif "currency" in cat or "single currency" in cat:
                            result["classification"]["asset_class"] = "fx_currency"
                        elif "crypto" in cat or "bitcoin" in cat or "digital" in cat:
                            result["classification"]["asset_class"] = "crypto"
                        else:
                            result["classification"]["asset_class"] = "other"
                    else:
                        # Mixed — use category to disambiguate
                        result["classification"]["asset_class"] = "mixed"
            except Exception:
                pass

            # Sector weightings (equity ETFs)
            try:
                sw = t.funds_data.sector_weightings
                if sw:
                    result["sector_weightings"] = {k: round(v, 4) for k, v in sw.items() if v > 0}
                    # Primary sector = largest weighting
                    if sw:
                        primary = max(sw, key=sw.get)
                        result["classification"]["sector"] = _normalize_sector(primary)
            except Exception:
                pass

            # Top holdings
            try:
                th = t.funds_data.top_holdings
                if th is not None and not th.empty:
                    holdings = []
                    for sym, row in th.iterrows():
                        holdings.append({
                            "ticker": sym,
                            "name": row.get("Name", ""),
                            "pct": round(float(row.get("Holding Percent", 0)), 4),
                        })
                    result["top_holdings"] = holdings
            except Exception:
                pass

            # Geography — infer from exchange and category
            exchange = info.get("exchange", "")
            category = (info.get("category") or "").lower()
            if any(x in exchange for x in ["NYQ", "PCX", "NMS", "NGM", "BTS", "ASE"]):
                if "international" in category or "foreign" in category or "emerging" in category:
                    result["classification"]["geography"] = "International"
                else:
                    result["classification"]["geography"] = "US"
            elif any(x in exchange for x in ["LSE", "AMS", "PAR", "FRA", "MIL"]):
                result["classification"]["geography"] = "Europe"
            elif any(x in exchange for x in ["CPH"]):
                result["classification"]["geography"] = "Denmark"
            elif any(x in exchange for x in ["TYO", "JPX"]):
                result["classification"]["geography"] = "Japan"
            else:
                result["classification"]["geography"] = exchange  # fallback to exchange code

            # Fill missing asset class from category if needed
            if not result["classification"]["asset_class"]:
                cat = (info.get("category") or "").lower()
                if "bond" in cat or "government" in cat or "treasury" in cat or "fixed" in cat:
                    result["classification"]["asset_class"] = "fixed_income"
                elif "commodit" in cat:
                    result["classification"]["asset_class"] = "commodities"
                elif "real estate" in cat or "reit" in cat:
                    result["classification"]["asset_class"] = "reits"
                elif "currency" in cat:
                    result["classification"]["asset_class"] = "fx_currency"
                elif any(x in cat for x in ["growth", "blend", "value", "cap", "equity", "stock"]):
                    result["classification"]["asset_class"] = "equities"
                else:
                    result["missing_fields"].append("asset_class")

            if not result["classification"]["sector"] and not result.get("sector_weightings"):
                # Bond/commodity ETFs won't have sector — that's expected, not missing
                if result["classification"]["asset_class"] == "equities":
                    result["missing_fields"].append("sector")

        else:
            # MUTUALFUND, INDEX, etc — try basic classification
            result["classification"]["asset_class"] = info.get("quoteType", "").lower()
            result["missing_fields"].append("asset_class")

    except Exception as e:
        result["error"] = str(e)

    return result


def _normalize_sector(raw_sector: str) -> str:
    """Normalize yfinance sector names to consistent labels."""
    mapping = {
        "technology": "Technology",
        "consumer_cyclical": "Consumer Cyclical",
        "consumer_defensive": "Consumer Defensive",
        "healthcare": "Healthcare",
        "financial_services": "Financial Services",
        "communication_services": "Communication Services",
        "industrials": "Industrials",
        "energy": "Energy",
        "utilities": "Utilities",
        "realestate": "Real Estate",
        "basic_materials": "Basic Materials",
    }
    return mapping.get(raw_sector, raw_sector)


# ── FX rate fetching ──────────────────────────────────────

def get_fx_rates(base_currency: str, target_currencies: list) -> dict:
    """Fetch FX rates to convert from each target currency to the base currency.

    Returns a dict: {currency_code: rate_to_base}
    The rate means: 1 unit of target currency = rate units of base currency.
    """
    rates = {}
    rates[base_currency] = 1.0  # base to base = 1

    for curr in target_currencies:
        if curr == base_currency:
            continue
        if curr in rates:
            continue

        try:
            # yfinance FX format: XXXYYY=X means 1 XXX = YYY price
            # We need: 1 curr = ? base
            if base_currency == "USD":
                # 1 curr = ? USD → fetch CURRUSD=X
                pair = f"{curr}USD=X"
                t = yf.Ticker(pair)
                hist = t.history(period="1d")
                if not hist.empty:
                    rates[curr] = round(float(hist["Close"].iloc[-1]), 6)
                else:
                    # Try inverse
                    pair = f"USD{curr}=X"
                    t = yf.Ticker(pair)
                    hist = t.history(period="1d")
                    if not hist.empty:
                        rates[curr] = round(1.0 / float(hist["Close"].iloc[-1]), 6)
            elif curr == "USD":
                # 1 USD = ? base → fetch USDBASE=X
                pair = f"USD{base_currency}=X"
                t = yf.Ticker(pair)
                hist = t.history(period="1d")
                if not hist.empty:
                    rates["USD"] = round(float(hist["Close"].iloc[-1]), 6)
                else:
                    pair = f"{base_currency}USD=X"
                    t = yf.Ticker(pair)
                    hist = t.history(period="1d")
                    if not hist.empty:
                        rates["USD"] = round(1.0 / float(hist["Close"].iloc[-1]), 6)
            else:
                # Cross rate via USD
                # 1 curr → USD → base
                curr_usd_pair = f"{curr}USD=X"
                t1 = yf.Ticker(curr_usd_pair)
                h1 = t1.history(period="1d")

                usd_base_pair = f"USD{base_currency}=X"
                t2 = yf.Ticker(usd_base_pair)
                h2 = t2.history(period="1d")

                if not h1.empty and not h2.empty:
                    curr_to_usd = float(h1["Close"].iloc[-1])
                    usd_to_base = float(h2["Close"].iloc[-1])
                    rates[curr] = round(curr_to_usd * usd_to_base, 6)

        except Exception:
            pass

        if curr not in rates:
            rates[curr] = None  # Flag as unavailable

    return rates


# ── Price refresh ─────────────────────────────────────────

def refresh_prices(config_path: str, user_config_path: str, output_dir: str):
    """Pull current prices for all external positions and save results."""
    config = json.loads(Path(config_path).read_text())
    user_config = json.loads(Path(user_config_path).read_text())
    base_currency = config.get("base_currency", user_config.get("base_currency", "USD"))

    positions = config.get("positions", [])
    if not positions:
        print("No external positions configured.")
        return

    # Collect all currencies we need FX rates for
    currencies_needed = set()
    for pos in positions:
        curr = pos.get("currency") or pos.get("classification", {}).get("currency_exposure")
        if curr:
            currencies_needed.add(curr)

    # Fetch FX rates
    print(f"Fetching FX rates (base: {base_currency})...")
    fx_rates = get_fx_rates(base_currency, list(currencies_needed))
    print(f"  Rates: {fx_rates}")

    # Refresh each position
    results = []
    total_value_base = 0.0
    stale_count = 0

    for pos in positions:
        ticker = pos["ticker"]
        quantity = pos["quantity"]
        entry_price = pos.get("entry_price")
        currency = pos.get("currency") or pos.get("classification", {}).get("currency_exposure", "USD")
        manual = pos.get("manual_valuation", False)

        if manual:
            # Use stored value
            current_price = pos.get("manual_current_price", entry_price or 0)
            stale = True
            print(f"  {ticker}: MANUAL — using stored value {current_price} {currency}")
        else:
            # Pull from yfinance
            try:
                t = yf.Ticker(ticker)
                hist = t.history(period="5d")
                if not hist.empty:
                    current_price = round(float(hist["Close"].iloc[-1]), 4)
                    last_date = hist.index[-1]
                    days_old = (datetime.now() - last_date.to_pydatetime().replace(tzinfo=None)).days
                    stale = days_old > 3
                    if stale:
                        stale_count += 1
                    print(f"  {ticker}: {current_price} {currency} (age: {days_old}d)")
                else:
                    current_price = entry_price or 0
                    stale = True
                    stale_count += 1
                    print(f"  {ticker}: NO DATA — using entry price {current_price}")
            except Exception as e:
                current_price = entry_price or 0
                stale = True
                stale_count += 1
                print(f"  {ticker}: ERROR ({e}) — using entry price {current_price}")

        # Calculate values
        value_native = current_price * quantity
        fx_rate = fx_rates.get(currency, 1.0)
        if fx_rate is None:
            fx_rate = 1.0  # fallback — will be flagged
            print(f"    WARNING: No FX rate for {currency}, using 1.0")

        value_base = round(value_native * fx_rate, 2)
        total_value_base += value_base

        # P&L (only if entry price provided)
        pl_absolute = None
        pl_pct = None
        if entry_price and entry_price > 0:
            pl_absolute = round((current_price - entry_price) * quantity, 2)
            pl_pct = round((current_price - entry_price) / entry_price * 100, 2)

        results.append({
            "ticker": ticker,
            "name": pos.get("name", ticker),
            "quantity": quantity,
            "currency": currency,
            "entry_price": entry_price,
            "current_price": current_price,
            "value_native": round(value_native, 2),
            "value_base": value_base,
            "fx_rate_to_base": fx_rate,
            "pl_absolute": pl_absolute,
            "pl_pct": pl_pct,
            "entry_date": pos.get("entry_date"),
            "account": pos.get("account"),
            "classification": pos.get("classification", {}),
            "sector_weightings": pos.get("sector_weightings"),
            "asset_classes": pos.get("asset_classes"),
            "manual_valuation": manual,
            "price_stale": stale,
        })

    # Calculate allocation percentages
    for r in results:
        r["allocation_pct"] = round(r["value_base"] / total_value_base * 100, 2) if total_value_base > 0 else 0

    # Save output
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    output = {
        "refresh_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "base_currency": base_currency,
        "fx_rates": fx_rates,
        "total_value_base": round(total_value_base, 2),
        "position_count": len(results),
        "stale_price_count": stale_count,
        "manual_valuation_count": sum(1 for r in results if r["manual_valuation"]),
        "positions": results,
    }

    out_file = output_path / "latest-prices.json"
    out_file.write_text(json.dumps(output, indent=2))
    print(f"\nSaved to {out_file}")
    print(f"Total external portfolio value: {total_value_base:,.2f} {base_currency}")
    print(f"Positions: {len(results)} | Stale: {stale_count} | Manual: {output['manual_valuation_count']}")

    return output


# ── Exposure aggregation ──────────────────────────────────

def aggregate_exposure(positions: list) -> dict:
    """Aggregate positions into exposure buckets by sector, geography, asset class, currency.

    For ETFs with sector_weightings, distributes allocation proportionally.
    For individual stocks, assigns full allocation to the stock's sector.
    """
    exposure = {
        "by_sector": {},
        "by_geography": {},
        "by_asset_class": {},
        "by_currency": {},
    }

    for pos in positions:
        alloc = pos.get("allocation_pct", 0)
        classification = pos.get("classification", {})

        # ── Currency exposure (always the position's denomination) ──
        curr = pos.get("currency", "Unknown")
        exposure["by_currency"][curr] = exposure["by_currency"].get(curr, 0) + alloc

        # ── Asset class ──
        ac = classification.get("asset_class", "Unknown")
        if pos.get("asset_classes"):
            # ETF with stock/bond/other split — distribute
            for cls, pct in pos["asset_classes"].items():
                if pct > 0:
                    label = _asset_class_label(cls)
                    exposure["by_asset_class"][label] = exposure["by_asset_class"].get(label, 0) + alloc * pct
        else:
            exposure["by_asset_class"][ac] = exposure["by_asset_class"].get(ac, 0) + alloc

        # ── Geography ──
        geo = classification.get("geography", "Unknown")
        exposure["by_geography"][geo] = exposure["by_geography"].get(geo, 0) + alloc

        # ── Sector ──
        if pos.get("sector_weightings"):
            # ETF with sector breakdown — distribute proportionally
            for sector, pct in pos["sector_weightings"].items():
                if pct > 0:
                    label = _normalize_sector(sector)
                    exposure["by_sector"][label] = exposure["by_sector"].get(label, 0) + alloc * pct
        elif classification.get("sector"):
            # Individual stock or ETF without sector data
            sector = classification["sector"]
            exposure["by_sector"][sector] = exposure["by_sector"].get(sector, 0) + alloc
        elif classification.get("asset_class") not in ("equities", None):
            # Non-equity (bonds, commodities, FX) — sector not applicable
            label = f"N/A ({classification.get('asset_class', 'other')})"
            exposure["by_sector"][label] = exposure["by_sector"].get(label, 0) + alloc

    # Round everything
    for dim in exposure:
        exposure[dim] = {k: round(v, 2) for k, v in sorted(exposure[dim].items(), key=lambda x: -x[1])}

    return exposure


def _asset_class_label(yf_key: str) -> str:
    """Convert yfinance asset_classes keys to readable labels."""
    mapping = {
        "stockPosition": "equities",
        "bondPosition": "fixed_income",
        "cashPosition": "cash",
        "preferredPosition": "preferred_stock",
        "convertiblePosition": "convertible_bonds",
        "otherPosition": "other",
    }
    return mapping.get(yf_key, yf_key)


# ── Snapshot management ───────────────────────────────────

def save_snapshot(config_path: str, user_config_path: str, output_dir: str):
    """Refresh prices and save a dated snapshot for historical tracking."""
    output = refresh_prices(config_path, user_config_path, output_dir)
    if not output:
        return

    output_path = Path(output_dir)

    # Save dated copy
    date_str = datetime.now().strftime("%Y-%m-%d")
    dated_file = output_path / f"{date_str}-external-snapshot.json"
    dated_file.write_text(json.dumps(output, indent=2))

    # Append to value history
    history_file = output_path / "external-value-history.json"
    if history_file.exists():
        history = json.loads(history_file.read_text())
    else:
        history = []

    # Avoid duplicate entries for the same date
    history = [h for h in history if h["date"] != date_str]
    history.append({
        "date": date_str,
        "total_value_base": output["total_value_base"],
        "base_currency": output["base_currency"],
        "position_count": output["position_count"],
    })
    history_file.write_text(json.dumps(history, indent=2))

    # Compute and save exposure
    exposure = aggregate_exposure(output["positions"])
    exposure_file = output_path / "latest-exposure.json"
    exposure_file.write_text(json.dumps(exposure, indent=2))

    print(f"\nDated snapshot: {dated_file}")
    print(f"Value history: {history_file} ({len(history)} entries)")
    print(f"Exposure: {exposure_file}")


# ── CLI ───────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="External Portfolio Utility")
    parser.add_argument("--action", required=True,
                        choices=["classify", "refresh_prices", "save_snapshot"],
                        help="Action to perform")
    parser.add_argument("--ticker", help="Ticker to classify (for classify action)")
    parser.add_argument("--config", help="Path to external-positions.json")
    parser.add_argument("--user-config", help="Path to user-config.json")
    parser.add_argument("--output", help="Output directory")

    args = parser.parse_args()

    if args.action == "classify":
        if not args.ticker:
            print("ERROR: --ticker required for classify action")
            sys.exit(1)
        result = classify_ticker(args.ticker)
        print(json.dumps(result, indent=2))

    elif args.action == "refresh_prices":
        if not args.config or not args.output:
            print("ERROR: --config and --output required for refresh_prices action")
            sys.exit(1)
        user_config = args.user_config or args.config.replace("external-positions", "user-config")
        refresh_prices(args.config, user_config, args.output)

    elif args.action == "save_snapshot":
        if not args.config or not args.output:
            print("ERROR: --config and --output required for save_snapshot action")
            sys.exit(1)
        user_config = args.user_config or args.config.replace("external-positions", "user-config")
        save_snapshot(args.config, user_config, args.output)


if __name__ == "__main__":
    main()
