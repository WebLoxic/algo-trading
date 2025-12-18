from typing import List, Optional

def rsi(values: List[float], period: int = 14) -> Optional[float]:
    if len(values) < period + 1:
        return None

    gains = 0.0
    losses = 0.0

    for i in range(-period, 0):
        diff = values[i] - values[i - 1]
        if diff > 0:
            gains += diff
        else:
            losses -= diff

    if losses == 0:
        return 100.0

    rs = gains / losses
    return 100 - (100 / (1 + rs))


def generate_signals(candles, period=14, overbought=70, oversold=30):
    closes, signals = [], []

    for c in candles:
        closes.append(float(c["close"]))
        val = rsi(closes, period)

        if val is None:
            signals.append(None)
        elif val < oversold:
            signals.append("BUY")
        elif val > overbought:
            signals.append("SELL")
        else:
            signals.append(None)

    return signals
