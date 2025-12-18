def optimize(candles, strategy_fn, param_grid, backtest_fn):
    best = {"pnl": float("-inf"), "params": None}

    for params in param_grid:
        signals = strategy_fn(candles, **params)
        result = backtest_fn(candles, signals)

        if result["pnl"] > best["pnl"]:
            best = {
                "pnl": result["pnl"],
                "params": params,
                "stats": result,
            }

    return best
