#!/usr/bin/env python3
"""
Performance Calculator — P&L Attribution, Drawdown, Sharpe

Reads portfolio snapshots and trade logs to compute:
- Total P&L and return
- Attribution: how much came from regime tilts vs thesis overlays
- Drawdown: max drawdown from high-water mark
- Sharpe ratio (annualized, using daily returns)
- Win rate by thesis type and mechanism

Usage:
    python performance_calculator.py --snapshots ../outputs/portfolio/ --trades ../outputs/trades/ --output ../outputs/performance/
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
import math


def load_snapshots(snapshot_dir: str) -> list:
    """Load all portfolio snapshots sorted by timestamp."""
    snapshots = []
    for f in sorted(Path(snapshot_dir).glob("*-snapshot.json")):
        if f.name == "latest-snapshot.json":
            continue
        with open(f, "r") as fh:
            snapshots.append(json.load(fh))
    return snapshots


def load_trade_logs(trades_dir: str) -> list:
    """Load all trade log entries."""
    trades = []
    for f in sorted(Path(trades_dir).glob("*.json")):
        with open(f, "r") as fh:
            data = json.load(fh)
            if isinstance(data, list):
                trades.extend(data)
            else:
                trades.append(data)
    return trades


def compute_returns(snapshots: list) -> dict:
    """Compute period returns from snapshot series."""
    if len(snapshots) < 2:
        return {
            "total_return_pct": 0,
            "daily_returns": [],
            "high_water_mark": snapshots[0]["account"]["portfolio_value"] if snapshots else 0,
            "max_drawdown_pct": 0,
            "current_drawdown_pct": 0,
        }

    daily_returns = []
    high_water_mark = snapshots[0]["account"]["portfolio_value"]
    max_drawdown = 0
    starting_value = snapshots[0]["account"]["portfolio_value"]

    for i in range(1, len(snapshots)):
        prev_val = snapshots[i - 1]["account"]["portfolio_value"]
        curr_val = snapshots[i]["account"]["portfolio_value"]

        if prev_val > 0:
            daily_ret = (curr_val - prev_val) / prev_val
            daily_returns.append({
                "date": snapshots[i]["timestamp"],
                "return_pct": round(daily_ret * 100, 4),
                "portfolio_value": curr_val,
            })

        if curr_val > high_water_mark:
            high_water_mark = curr_val

        drawdown = (high_water_mark - curr_val) / high_water_mark if high_water_mark > 0 else 0
        if drawdown > max_drawdown:
            max_drawdown = drawdown

    ending_value = snapshots[-1]["account"]["portfolio_value"]
    total_return = (ending_value - starting_value) / starting_value if starting_value > 0 else 0
    current_dd = (high_water_mark - ending_value) / high_water_mark if high_water_mark > 0 else 0

    return {
        "starting_value": starting_value,
        "ending_value": ending_value,
        "total_return_pct": round(total_return * 100, 4),
        "daily_returns": daily_returns,
        "high_water_mark": high_water_mark,
        "max_drawdown_pct": round(max_drawdown * 100, 4),
        "current_drawdown_pct": round(current_dd * 100, 4),
    }


def compute_sharpe(daily_returns: list, risk_free_annual: float = 0.045) -> float:
    """Annualized Sharpe ratio from daily returns. Risk-free default: 4.5% (current T-bill approx)."""
    if len(daily_returns) < 5:
        return 0.0

    returns = [r["return_pct"] / 100 for r in daily_returns]
    mean_ret = sum(returns) / len(returns)

    if len(returns) > 1:
        variance = sum((r - mean_ret) ** 2 for r in returns) / (len(returns) - 1)
        std_ret = math.sqrt(variance)
    else:
        return 0.0

    if std_ret == 0:
        return 0.0

    # Annualize: assume ~252 trading days
    daily_rf = risk_free_annual / 252
    excess_return = mean_ret - daily_rf
    annualized_sharpe = (excess_return / std_ret) * math.sqrt(252)

    return round(annualized_sharpe, 3)


def compute_attribution(trade_logs: list) -> dict:
    """
    Attribution: separate performance by layer (regime vs thesis)
    and by thesis mechanism type.
    """
    by_layer = {"regime": [], "thesis_tactical": [], "thesis_structural": []}
    by_mechanism = {}
    by_thesis = {}

    for trade in trade_logs:
        layer = trade.get("layer", "regime")
        if layer not in by_layer:
            by_layer[layer] = []
        by_layer[layer].append(trade)

        mechanism = trade.get("mechanism_type", "unknown")
        if mechanism not in by_mechanism:
            by_mechanism[mechanism] = []
        by_mechanism[mechanism].append(trade)

        thesis_name = trade.get("thesis", "")
        if thesis_name:
            if thesis_name not in by_thesis:
                by_thesis[thesis_name] = []
            by_thesis[thesis_name].append(trade)

    return {
        "trade_count_by_layer": {k: len(v) for k, v in by_layer.items()},
        "trade_count_by_mechanism": {k: len(v) for k, v in by_mechanism.items()},
        "trade_count_by_thesis": {k: len(v) for k, v in by_thesis.items()},
    }


def compute_win_rate(trade_logs: list) -> dict:
    """Win rate for closed trades that have realized P&L."""
    closed = [t for t in trade_logs if t.get("realized_pl") is not None]
    if not closed:
        return {"total_closed": 0, "win_rate": None, "avg_win": None, "avg_loss": None}

    wins = [t for t in closed if t["realized_pl"] > 0]
    losses = [t for t in closed if t["realized_pl"] <= 0]

    avg_win = sum(t["realized_pl"] for t in wins) / len(wins) if wins else 0
    avg_loss = sum(t["realized_pl"] for t in losses) / len(losses) if losses else 0

    return {
        "total_closed": len(closed),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": round(len(wins) / len(closed) * 100, 1) if closed else None,
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "profit_factor": round(abs(avg_win / avg_loss), 2) if avg_loss != 0 else None,
    }


def fetch_benchmark_data(start_date: str, end_date: str, snapshot_dates: list) -> dict:
    """Fetch SPY and TLT returns aligned to portfolio snapshot dates.

    Returns cumulative % return series for SPY, plus total returns for SPY,
    TLT, and a 60/40 blend. Gracefully returns error dict on any failure.
    """
    try:
        import yfinance as yf
    except ImportError:
        return {"error": "yfinance not installed"}

    try:
        from datetime import datetime as _dt, timedelta as _td

        # Pad start date 7 days earlier to guarantee a baseline close
        start_dt = _dt.strptime(start_date, "%Y-%m-%d") - _td(days=7)
        padded_start = start_dt.strftime("%Y-%m-%d")
        # Pad end date 1 day forward for yfinance end-exclusive range
        end_dt = _dt.strptime(end_date, "%Y-%m-%d") + _td(days=1)
        padded_end = end_dt.strftime("%Y-%m-%d")

        spy_hist = yf.Ticker("SPY").history(start=padded_start, end=padded_end)
        tlt_hist = yf.Ticker("TLT").history(start=padded_start, end=padded_end)

        if spy_hist.empty:
            return {"error": "No SPY data returned from yfinance"}

        # Convert to dict: date_str -> close price
        def _to_price_dict(hist):
            d = {}
            for idx, row in hist.iterrows():
                d[idx.strftime("%Y-%m-%d")] = float(row["Close"])
            return d

        spy_prices = _to_price_dict(spy_hist)
        tlt_prices = _to_price_dict(tlt_hist) if not tlt_hist.empty else {}

        # Sorted trading dates for lookup
        spy_dates_sorted = sorted(spy_prices.keys())
        tlt_dates_sorted = sorted(tlt_prices.keys()) if tlt_prices else []

        def _nearest_price(target_date, prices, sorted_dates):
            """Find close price for nearest trading day <= target_date."""
            best = None
            for d in sorted_dates:
                if d <= target_date:
                    best = d
                else:
                    break
            return prices[best] if best else None

        # Get baseline prices (nearest trading day <= first snapshot date)
        spy_base = _nearest_price(start_date, spy_prices, spy_dates_sorted)
        tlt_base = _nearest_price(start_date, tlt_prices, tlt_dates_sorted) if tlt_prices else None

        if spy_base is None or spy_base == 0:
            return {"error": f"No SPY baseline price for {start_date}"}

        # Build cumulative % return aligned to snapshot dates
        spy_returns_by_date = {}
        for date_str in snapshot_dates:
            price = _nearest_price(date_str, spy_prices, spy_dates_sorted)
            if price is not None:
                spy_returns_by_date[date_str] = round((price - spy_base) / spy_base * 100, 2)

        # Total returns
        spy_end = _nearest_price(end_date, spy_prices, spy_dates_sorted)
        spy_return_pct = round((spy_end - spy_base) / spy_base * 100, 4) if spy_end else 0

        tlt_return_pct = 0.0
        if tlt_base and tlt_base > 0:
            tlt_end = _nearest_price(end_date, tlt_prices, tlt_dates_sorted)
            if tlt_end:
                tlt_return_pct = round((tlt_end - tlt_base) / tlt_base * 100, 4)

        balanced_return_pct = round(0.6 * spy_return_pct + 0.4 * tlt_return_pct, 4)

        return {
            "spy_return_pct": spy_return_pct,
            "spy_returns_by_date": spy_returns_by_date,
            "tlt_return_pct": tlt_return_pct,
            "balanced_return_pct": balanced_return_pct,
            "error": None,
        }

    except Exception as e:
        return {"error": str(e)}


def generate_weekly_report(snapshots: list, trade_logs: list) -> dict:
    """Compile full weekly performance report."""
    returns = compute_returns(snapshots)
    sharpe = compute_sharpe(returns["daily_returns"])
    attribution = compute_attribution(trade_logs)
    win_rate = compute_win_rate(trade_logs)

    return {
        "generated_at": datetime.now().isoformat(),
        "period": {
            "start": snapshots[0]["timestamp"] if snapshots else None,
            "end": snapshots[-1]["timestamp"] if snapshots else None,
            "snapshot_count": len(snapshots),
        },
        "returns": returns,
        "sharpe_ratio": sharpe,
        "attribution": attribution,
        "win_rate": win_rate,
        "risk": {
            "max_drawdown_pct": returns["max_drawdown_pct"],
            "current_drawdown_pct": returns["current_drawdown_pct"],
            "high_water_mark": returns["high_water_mark"],
            "drawdown_breach": returns["max_drawdown_pct"] >= 10.0,
        },
    }


def main():
    parser = argparse.ArgumentParser(description="Performance Calculator")
    parser.add_argument("--snapshots", required=True, help="Portfolio snapshots directory")
    parser.add_argument("--trades", required=True, help="Trade logs directory")
    parser.add_argument("--output", required=True, help="Output directory")

    args = parser.parse_args()

    snapshots = load_snapshots(args.snapshots)
    trade_logs = load_trade_logs(args.trades)
    report = generate_weekly_report(snapshots, trade_logs)

    os.makedirs(args.output, exist_ok=True)
    dated_path = os.path.join(args.output,
                               f"{datetime.now().strftime('%Y-%m-%d')}-performance.json")
    latest_path = os.path.join(args.output, "latest-performance-report.json")

    with open(dated_path, "w") as f:
        json.dump(report, f, indent=2)
    with open(latest_path, "w") as f:
        json.dump(report, f, indent=2)

    print(f"Performance report saved to {dated_path}")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
