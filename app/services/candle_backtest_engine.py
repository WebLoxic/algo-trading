from app.services.candle_loader import load_candles
from app.services.candle_strategy import generate_signals


def run_candle_backtest(
    symbol,
    interval,
    start,
    end,
    slippage_pct,
    commission,
):
    candles = load_candles(symbol, interval, start, end)
    signals = generate_signals(candles)

    position = 0
    entry_price = 0
    equity = 0
    peak = 0
    max_dd = 0
    trades = []

    for i in range(len(candles)):
        signal = signals[i]
        price = float(candles[i]["close"])

        if signal == "BUY" and position == 0:
            entry_price = price * (1 + slippage_pct / 100)
            position = 1

        elif signal == "SELL" and position == 1:
            exit_price = price * (1 - slippage_pct / 100)
            pnl = (exit_price - entry_price) - commission
            equity += pnl
            trades.append(pnl)
            position = 0

        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)

    wins = len([x for x in trades if x > 0])

    return {
        "trades": len(trades),
        "pnl": round(equity, 2),
        "win_rate": round((wins / len(trades)) * 100, 2) if trades else 0,
        "max_drawdown": round((max_dd / peak) * 100, 2) if peak else 0,
    }
