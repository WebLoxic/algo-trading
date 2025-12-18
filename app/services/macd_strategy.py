from typing import List, Optional

def ema(values: List[float], period: int) -> Optional[float]:
    if len(values) < period:
        return None
    k = 2 / (period + 1)
    ema_val = sum(values[:period]) / period
    for v in values[period:]:
        ema_val = v * k + ema_val * (1 - k)
    return ema_val


def generate_signals(candles, fast=12, slow=26, signal_period=9):
    closes, macd_vals, signals = [], [], []
    prev_macd, prev_signal = None, None

    for c in candles:
        closes.append(float(c["close"]))
        fast_ema = ema(closes, fast)
        slow_ema = ema(closes, slow)

        if fast_ema is None or slow_ema is None:
            signals.append(None)
            continue

        macd = fast_ema - slow_ema
        macd_vals.append(macd)
        signal_line = ema(macd_vals, signal_period)

        sig = None
        if (
            prev_macd is not None
            and prev_signal is not None
            and signal_line is not None
        ):
            if prev_macd <= prev_signal and macd > signal_line:
                sig = "BUY"
            elif prev_macd >= prev_signal and macd < signal_line:
                sig = "SELL"

        signals.append(sig)
        prev_macd, prev_signal = macd, signal_line

    return signals
