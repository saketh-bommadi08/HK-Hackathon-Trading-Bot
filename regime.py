import math


def detect_regime(df):
    if df is None or len(df) < 21:
        return "NO_TRADE"

    try:
        latest = df.iloc[-1]

        close = float(latest["close"])
        ema_9 = float(latest["ema_9"])
        ema_21 = float(latest["ema_21"])
        volatility = float(latest["volatility"])

        if (
            not math.isfinite(close)
            or not math.isfinite(ema_9)
            or not math.isfinite(ema_21)
            or not math.isfinite(volatility)
            or close <= 0
            or volatility < 0
        ):
            return "NO_TRADE"

        ema_distance = abs(ema_9 - ema_21) / close

        if ema_9 > ema_21 and ema_distance > 0.001:
            return "TRENDING_UP"

        if ema_9 < ema_21 and ema_distance > 0.001:
            return "TRENDING_DOWN"

        if ema_distance <= 0.001:
            return "RANGING"

        return "NO_TRADE"

    except (TypeError, ValueError, KeyError, IndexError):
        return "NO_TRADE"
