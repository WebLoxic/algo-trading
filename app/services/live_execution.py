from app.services.trading_engine import place_market_order

def execute_signal(user_id, symbol, signal, qty):
    if signal not in ("BUY", "SELL"):
        return None

    return place_market_order(
        user_id=user_id,
        symbol=symbol,
        side=signal,
        quantity=qty,
    )
