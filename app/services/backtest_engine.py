from sqlalchemy import text
from app.db import SessionLocal


def load_ticks(symbol, start, end, dataset):
    db = SessionLocal()
    try:
        rows = db.execute(
            text("""
                SELECT price, ts
                FROM market_ticks
                WHERE symbol = :sym
                  AND ts BETWEEN :f AND :t
                ORDER BY ts ASC
            """),
            {"sym": symbol, "f": start, "t": end},
        ).fetchall()

        # fallback demo ticks
        if not rows:
            price = 2400
            rows = []
            for i in range(500):
                price += (1 if i % 3 else -1)
                rows.append({"price": price, "ts": i})

        return rows
    finally:
        db.close()


def run_backtest(symbol, start, end, slippage_pct, commission, dataset):
    ticks = load_ticks(symbol, start, end, dataset)

    position = 0
    entry_price = 0
    trades = []
    equity = 0
    peak = 0
    max_dd = 0

    for i, tick in enumerate(ticks):
        price = float(tick["price"])

        # Simple strategy: BUY every 20 ticks, SELL after 10
        if position == 0 and i % 20 == 0:
            entry_price = price * (1 + slippage_pct / 100)
            position = 1

        elif position == 1 and i % 20 == 10:
            exit_price = price * (1 - slippage_pct / 100)
            pnl = (exit_price - entry_price) - commission
            equity += pnl
            trades.append(pnl)
            position = 0

        peak = max(peak, equity)
        dd = peak - equity
        max_dd = max(max_dd, dd)

    wins = len([x for x in trades if x > 0])

    return {
        "trades": len(trades),
        "pnl": round(equity, 2),
        "win_rate": round((wins / len(trades)) * 100, 2) if trades else 0,
        "max_drawdown": round((max_dd / peak) * 100, 2) if peak else 0,
    }
