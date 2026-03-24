#!/usr/bin/env python3
"""
Trade Executor — Alpaca Paper Trading Wrapper

All Alpaca API interactions go through this script. No other skill
or script touches the API directly.

Usage:
    python trade_executor.py --action snapshot --config ../config/user-config.json --output ../outputs/portfolio/
    python trade_executor.py --action submit_order --config ../config/user-config.json --order-file order.json
    python trade_executor.py --action close_position --config ../config/user-config.json --symbol SPY
    python trade_executor.py --action close_all --config ../config/user-config.json
    python trade_executor.py --action history --config ../config/user-config.json --output ../outputs/portfolio/
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    from alpaca.trading.client import TradingClient
    from alpaca.trading.requests import (
        MarketOrderRequest,
        LimitOrderRequest,
        StopOrderRequest,
        GetOrdersRequest,
    )
    from alpaca.trading.enums import OrderSide, TimeInForce, OrderType, QueryOrderStatus
except ImportError:
    print("ERROR: alpaca-py not installed. Run: pip install alpaca-py --break-system-packages")
    sys.exit(1)


def load_config(config_path: str) -> dict:
    """Load user configuration with API keys."""
    with open(config_path, "r") as f:
        return json.load(f)


def get_client(config: dict) -> TradingClient:
    """Initialize Alpaca TradingClient for paper trading."""
    return TradingClient(
        api_key=config["alpaca_api_key"],
        secret_key=config["alpaca_secret_key"],
        paper=True,
    )


def get_account_snapshot(client: TradingClient) -> dict:
    """Get current account state."""
    account = client.get_account()
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "account_id": str(account.id),
        "status": str(account.status),
        "cash": float(account.cash),
        "portfolio_value": float(account.portfolio_value),
        "equity": float(account.equity),
        "last_equity": float(account.last_equity),
        "buying_power": float(account.buying_power),
        "long_market_value": float(account.long_market_value),
        "short_market_value": float(account.short_market_value),
        "initial_margin": float(account.initial_margin),
        "maintenance_margin": float(account.maintenance_margin),
        "daytrade_count": int(account.daytrade_count),
        "pattern_day_trader": bool(account.pattern_day_trader),
        "trading_blocked": bool(account.trading_blocked),
        "multiplier": str(account.multiplier),
        "currency": str(account.currency),
    }


def get_positions(client: TradingClient) -> list:
    """Get all current positions — returns sizes and symbols only, NO P&L."""
    positions = client.get_all_positions()
    result = []
    for pos in positions:
        result.append({
            "symbol": str(pos.symbol),
            "qty": float(pos.qty),
            "side": str(pos.side),
            "market_value": float(pos.market_value),
            "current_price": float(pos.current_price),
            "avg_entry_price": float(pos.avg_entry_price),
            "asset_class": str(pos.asset_class),
        })
    return result


def get_positions_with_pnl(client: TradingClient) -> list:
    """Get positions WITH P&L — only for T6 performance tracking, never for T3 reasoning."""
    positions = client.get_all_positions()
    result = []
    for pos in positions:
        result.append({
            "symbol": str(pos.symbol),
            "qty": float(pos.qty),
            "side": str(pos.side),
            "market_value": float(pos.market_value),
            "current_price": float(pos.current_price),
            "avg_entry_price": float(pos.avg_entry_price),
            "unrealized_pl": float(pos.unrealized_pl),
            "unrealized_plpc": float(pos.unrealized_plpc),
            "change_today": float(pos.change_today),
            "asset_class": str(pos.asset_class),
        })
    return result


def get_recent_orders(client: TradingClient, limit: int = 50) -> list:
    """Get recent orders for logging."""
    request = GetOrdersRequest(
        status=QueryOrderStatus.ALL,
        limit=limit,
    )
    orders = client.get_orders(request)
    result = []
    for order in orders:
        result.append({
            "id": str(order.id),
            "symbol": str(order.symbol),
            "side": str(order.side),
            "type": str(order.type),
            "qty": str(order.qty),
            "filled_qty": str(order.filled_qty) if order.filled_qty else "0",
            "filled_avg_price": str(order.filled_avg_price) if order.filled_avg_price else None,
            "status": str(order.status),
            "submitted_at": str(order.submitted_at) if order.submitted_at else None,
            "filled_at": str(order.filled_at) if order.filled_at else None,
            "time_in_force": str(order.time_in_force),
            "limit_price": str(order.limit_price) if order.limit_price else None,
            "stop_price": str(order.stop_price) if order.stop_price else None,
        })
    return result


def submit_order(client: TradingClient, order_spec: dict) -> dict:
    """
    Submit a single order. order_spec format:
    {
        "symbol": "SPY",
        "side": "buy",          # buy or sell
        "qty": 10,              # shares (int or float for fractional)
        "type": "market",       # market, limit, stop
        "time_in_force": "day", # day, gtc
        "limit_price": null,    # required for limit orders
        "stop_price": null,     # required for stop orders
        "reason": "..."         # logged but not sent to Alpaca
    }
    """
    side = OrderSide.BUY if order_spec["side"].lower() == "buy" else OrderSide.SELL
    tif = TimeInForce.DAY if order_spec.get("time_in_force", "day") == "day" else TimeInForce.GTC

    order_type = order_spec.get("type", "market").lower()

    if order_type == "market":
        request = MarketOrderRequest(
            symbol=order_spec["symbol"],
            qty=order_spec["qty"],
            side=side,
            time_in_force=tif,
        )
    elif order_type == "limit":
        if not order_spec.get("limit_price"):
            raise ValueError(f"Limit order for {order_spec['symbol']} requires limit_price")
        request = LimitOrderRequest(
            symbol=order_spec["symbol"],
            qty=order_spec["qty"],
            side=side,
            time_in_force=tif,
            limit_price=order_spec["limit_price"],
        )
    elif order_type == "stop":
        if not order_spec.get("stop_price"):
            raise ValueError(f"Stop order for {order_spec['symbol']} requires stop_price")
        request = StopOrderRequest(
            symbol=order_spec["symbol"],
            qty=order_spec["qty"],
            side=side,
            time_in_force=tif,
            stop_price=order_spec["stop_price"],
        )
    else:
        raise ValueError(f"Unsupported order type: {order_type}")

    try:
        order = client.submit_order(request)
        return {
            "success": True,
            "order_id": str(order.id),
            "symbol": str(order.symbol),
            "side": str(order.side),
            "type": str(order.type),
            "qty": str(order.qty),
            "status": str(order.status),
            "submitted_at": str(order.submitted_at),
            "limit_price": str(order.limit_price) if order.limit_price else None,
            "stop_price": str(order.stop_price) if order.stop_price else None,
        }
    except Exception as e:
        return {
            "success": False,
            "symbol": order_spec["symbol"],
            "error": str(e),
        }


def submit_orders_batch(client: TradingClient, orders: list) -> list:
    """Submit multiple orders. Returns list of results."""
    results = []
    for order_spec in orders:
        result = submit_order(client, order_spec)
        result["reason"] = order_spec.get("reason", "")
        result["thesis"] = order_spec.get("thesis", "")
        result["layer"] = order_spec.get("layer", "regime")
        results.append(result)
    return results


def close_position(client: TradingClient, symbol: str) -> dict:
    """Close a specific position entirely."""
    try:
        order = client.close_position(symbol)
        return {
            "success": True,
            "symbol": symbol,
            "order_id": str(order.id) if hasattr(order, 'id') else str(order),
            "action": "close_position",
        }
    except Exception as e:
        return {
            "success": False,
            "symbol": symbol,
            "error": str(e),
            "action": "close_position",
        }


def close_all_positions(client: TradingClient) -> dict:
    """Close all positions — emergency use only."""
    try:
        result = client.close_all_positions(cancel_orders=True)
        return {
            "success": True,
            "action": "close_all",
            "result": str(result),
        }
    except Exception as e:
        return {
            "success": False,
            "action": "close_all",
            "error": str(e),
        }


def cancel_all_open_orders(client: TradingClient) -> dict:
    """Cancel all pending orders."""
    try:
        result = client.cancel_orders()
        return {
            "success": True,
            "action": "cancel_all_orders",
            "result": str(result),
        }
    except Exception as e:
        return {
            "success": False,
            "action": "cancel_all_orders",
            "error": str(e),
        }


def take_full_snapshot(client: TradingClient) -> dict:
    """Complete portfolio snapshot for T0."""
    account = get_account_snapshot(client)
    positions = get_positions(client)
    orders = get_recent_orders(client, limit=20)

    # Compute allocation percentages
    portfolio_value = account["portfolio_value"]
    allocations = {}
    if portfolio_value > 0:
        cash_pct = (account["cash"] / portfolio_value) * 100
        allocations["cash"] = round(cash_pct, 2)
        for pos in positions:
            symbol_pct = (pos["market_value"] / portfolio_value) * 100
            allocations[pos["symbol"]] = round(symbol_pct, 2)

    return {
        "timestamp": account["timestamp"],
        "account": account,
        "positions": positions,
        "positions_count": len(positions),
        "allocations_pct": allocations,
        "recent_orders": orders,
    }


def take_performance_snapshot(client: TradingClient) -> dict:
    """Full snapshot WITH P&L — only for T6 performance tracking."""
    account = get_account_snapshot(client)
    positions = get_positions_with_pnl(client)

    total_unrealized_pl = sum(p["unrealized_pl"] for p in positions)

    return {
        "timestamp": account["timestamp"],
        "account": account,
        "positions": positions,
        "total_unrealized_pl": round(total_unrealized_pl, 2),
        "total_unrealized_plpc": round(
            (total_unrealized_pl / account["portfolio_value"] * 100) if account["portfolio_value"] > 0 else 0, 4
        ),
    }


def main():
    parser = argparse.ArgumentParser(description="Alpaca Paper Trading Executor")
    parser.add_argument("--action", required=True,
                        choices=["snapshot", "performance_snapshot", "submit_order",
                                 "submit_batch", "close_position", "close_all",
                                 "cancel_orders", "orders"],
                        help="Action to perform")
    parser.add_argument("--config", required=True, help="Path to user-config.json")
    parser.add_argument("--output", help="Output directory for snapshots")
    parser.add_argument("--order-file", help="JSON file with order spec(s)")
    parser.add_argument("--symbol", help="Symbol for close_position")

    args = parser.parse_args()

    config = load_config(args.config)
    client = get_client(config)

    if args.action == "snapshot":
        result = take_full_snapshot(client)
        if args.output:
            os.makedirs(args.output, exist_ok=True)
            # Save as latest and timestamped
            latest_path = os.path.join(args.output, "latest-snapshot.json")
            dated_path = os.path.join(args.output,
                                       f"{datetime.now().strftime('%Y-%m-%d-%H%M')}-snapshot.json")
            with open(latest_path, "w") as f:
                json.dump(result, f, indent=2)
            with open(dated_path, "w") as f:
                json.dump(result, f, indent=2)
            print(f"Snapshot saved to {latest_path} and {dated_path}")
        else:
            print(json.dumps(result, indent=2))

    elif args.action == "performance_snapshot":
        result = take_performance_snapshot(client)
        if args.output:
            os.makedirs(args.output, exist_ok=True)
            path = os.path.join(args.output, "latest-performance.json")
            with open(path, "w") as f:
                json.dump(result, f, indent=2)
            print(f"Performance snapshot saved to {path}")
        else:
            print(json.dumps(result, indent=2))

    elif args.action == "submit_order":
        if not args.order_file:
            print("ERROR: --order-file required for submit_order")
            sys.exit(1)
        with open(args.order_file, "r") as f:
            order_spec = json.load(f)
        result = submit_order(client, order_spec)
        print(json.dumps(result, indent=2))

    elif args.action == "submit_batch":
        if not args.order_file:
            print("ERROR: --order-file required for submit_batch")
            sys.exit(1)
        with open(args.order_file, "r") as f:
            orders = json.load(f)
        results = submit_orders_batch(client, orders)
        print(json.dumps(results, indent=2))
        # Also save to output if specified
        if args.output:
            os.makedirs(args.output, exist_ok=True)
            path = os.path.join(args.output,
                                f"{datetime.now().strftime('%Y-%m-%d-%H%M')}-batch-results.json")
            with open(path, "w") as f:
                json.dump(results, f, indent=2)

    elif args.action == "close_position":
        if not args.symbol:
            print("ERROR: --symbol required for close_position")
            sys.exit(1)
        result = close_position(client, args.symbol)
        print(json.dumps(result, indent=2))

    elif args.action == "close_all":
        result = close_all_positions(client)
        print(json.dumps(result, indent=2))

    elif args.action == "cancel_orders":
        result = cancel_all_open_orders(client)
        print(json.dumps(result, indent=2))

    elif args.action == "orders":
        result = get_recent_orders(client)
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
