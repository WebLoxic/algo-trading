# def sma(values, period):
#     if len(values) < period:
#         return None
#     return sum(values[-period:]) / period


# def generate_signals(candles, fast=5, slow=20):
#     closes = []
#     signals = []

#     prev_fast = None
#     prev_slow = None

#     for c in candles:
#         closes.append(float(c["close"]))

#         fast_sma = sma(closes, fast)
#         slow_sma = sma(closes, slow)

#         if fast_sma is None or slow_sma is None:
#             signals.append(None)
#             prev_fast = fast_sma
#             prev_slow = slow_sma
#             continue

#         # 🔥 CROSSOVER LOGIC (IMPORTANT)
#         if prev_fast is not None and prev_slow is not None:
#             if prev_fast <= prev_slow and fast_sma > slow_sma:
#                 signals.append("BUY")
#             elif prev_fast >= prev_slow and fast_sma < slow_sma:
#                 signals.append("SELL")
#             else:
#                 signals.append(None)
#         else:
#             signals.append(None)

#         prev_fast = fast_sma
#         prev_slow = slow_sma

#     return signals





"""
Candle Strategy: SMA Crossover (Production Ready)

- No look-ahead bias
- Proper crossover detection (no signal spam)
- Configurable periods
- Safe for backtest + live execution
"""

from typing import List, Optional


def sma(values: List[float], period: int) -> Optional[float]:
    if len(values) < period:
        return None
    return sum(values[-period:]) / period


def generate_signals(
    candles: List[dict],
    fast_period: int = 5,
    slow_period: int = 20,
) -> List[Optional[str]]:
    """
    Returns array aligned with candles:
    - "BUY"  → bullish crossover
    - "SELL" → bearish crossover
    - None   → no action
    """

    closes: List[float] = []
    signals: List[Optional[str]] = []

    prev_fast: Optional[float] = None
    prev_slow: Optional[float] = None

    for candle in candles:
        close = float(candle["close"])
        closes.append(close)

        fast_sma = sma(closes, fast_period)
        slow_sma = sma(closes, slow_period)

        signal = None

        if (
            fast_sma is not None
            and slow_sma is not None
            and prev_fast is not None
            and prev_slow is not None
        ):
            # 🔥 Bullish crossover
            if prev_fast <= prev_slow and fast_sma > slow_sma:
                signal = "BUY"

            # 🔥 Bearish crossover
            elif prev_fast >= prev_slow and fast_sma < slow_sma:
                signal = "SELL"

        signals.append(signal)

        prev_fast = fast_sma
        prev_slow = slow_sma

    return signals
