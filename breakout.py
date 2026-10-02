import math


def detect_breakout(df):
    if df is None or len(df) < 21:
        return "NO_TRADE"

    try:
        latest = df.iloc[-1]

        close = float(latest["close"])
        volatility = float(latest["volatility"])

        if (
            not math.isfinite(close)
            or not math.isfinite(volatility)
            or close <= 0
            or volatility <= 0
        ):
            return "NO_TRADE"

        recent_high = float(df["high"].iloc[-21:-1].max())
        recent_low = float(df["low"].iloc[-21:-1].min())

        if not math.isfinite(recent_high) or not math.isfinite(recent_low):
            return "NO_TRADE"

        breakout_buffer = close * 0.0005

        if close > recent_high + breakout_buffer:
            return "BUY"

        if close < recent_low - breakout_buffer:
            return "SELL"

        return "NO_TRADE"

    except (TypeError, ValueError, KeyError, IndexError):
        return "NO_TRADE"
