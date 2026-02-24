"""Find top 10 options contracts traded today by volume, open interest, and premium paid.

Usage:
    python top_options_contracts.py --ticker SPY --top-n 10
    python top_options_contracts.py --ticker AAPL --expiry 2026-01-16
"""

from __future__ import annotations

import argparse
import sys
from typing import Optional

import pandas as pd
import yfinance as yf


CONTRACT_MULTIPLIER = 100


def get_options_chain(ticker: str, expiry: Optional[str] = None) -> pd.DataFrame:
    """Return combined calls/puts for the given ticker and expiry."""
    tk = yf.Ticker(ticker)
    expiries = list(tk.options)

    if not expiries:
        raise ValueError(f"No option expiries found for ticker '{ticker}'.")

    selected_expiry = expiry or expiries[0]
    if selected_expiry not in expiries:
        available = ", ".join(expiries)
        raise ValueError(
            f"Expiry '{selected_expiry}' is not available for '{ticker}'. "
            f"Available expiries: {available}"
        )

    chain = tk.option_chain(selected_expiry)
    calls = chain.calls.copy()
    puts = chain.puts.copy()

    calls["optionType"] = "call"
    puts["optionType"] = "put"

    df = pd.concat([calls, puts], ignore_index=True)
    df["expiry"] = selected_expiry

    # Approximate premium traded today = today's volume * last trade price * contract multiplier.
    df["premiumPaid"] = (
        df["volume"].fillna(0).astype(float)
        * df["lastPrice"].fillna(0).astype(float)
        * CONTRACT_MULTIPLIER
    )

    return df


def top_contracts(df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """Rank contracts by volume, open interest, and premium paid and return top N."""
    ranked = (
        df.sort_values(
            by=["volume", "openInterest", "premiumPaid"],
            ascending=[False, False, False],
        )
        .head(top_n)
        .copy()
    )

    cols = [
        "contractSymbol",
        "optionType",
        "expiry",
        "strike",
        "lastPrice",
        "volume",
        "openInterest",
        "premiumPaid",
        "impliedVolatility",
        "inTheMoney",
    ]

    ranked = ranked[cols]
    return ranked


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Find top options contracts traded today, ranked by volume, open interest, "
            "and estimated premium paid."
        )
    )
    parser.add_argument("--ticker", required=True, help="Underlying ticker symbol, e.g., SPY")
    parser.add_argument(
        "--expiry",
        help="Option expiry in YYYY-MM-DD. Defaults to nearest available expiry.",
    )
    parser.add_argument("--top-n", type=int, default=10, help="Number of rows to return")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        df = get_options_chain(args.ticker.upper(), args.expiry)
        result = top_contracts(df, args.top_n)
    except Exception as exc:  # pragma: no cover - CLI-safe error handling
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if result.empty:
        print("No option contracts returned.")
        return 0

    pd.set_option("display.max_colwidth", 40)
    print(result.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
