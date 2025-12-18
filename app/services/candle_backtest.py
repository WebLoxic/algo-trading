def backtest(candles, signals, slippage=0.0, commission=0.0):
    position = None
    entry = 0.0
    pnl = 0.0
    trades = 0

    for c, s in zip(candles, signals):
        price = float(c["close"])

        if s == "BUY" and position is None:
            entry = price * (1 + slippage)
            position = "LONG"
            trades += 1

        elif s == "SELL" and position == "LONG":
            exit_price = price * (1 - slippage)
            pnl += exit_price - entry - commission
            position = None

    return {
        "pnl": round(pnl, 2),
        "trades": trades,
    }
