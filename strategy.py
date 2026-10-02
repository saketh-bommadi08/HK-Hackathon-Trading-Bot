from breakout import detect_breakout

RANGE_LOOKBACK = 20
RANGE_ENTRY_Z = 1.0
TREND_STRENGTH_FULL = 0.003


def trend_strategy(df, regime):
    try:
        latest = df.iloc[-1]
        close = float(latest["close"])
        ema_9 = float(latest["ema_9"])
        ema_21 = float(latest["ema_21"])

        if close <= 0:
            return "NO_TRADE", 0.0

        ema_distance = abs(ema_9 - ema_21) / close

        if regime == "TRENDING_UP" and close > ema_9 and ema_9 > ema_21:
            strength = min(1.0, ema_distance / TREND_STRENGTH_FULL)
            return "BUY", strength

        if regime == "TRENDING_DOWN" and close < ema_9 and ema_9 < ema_21:
            strength = min(1.0, ema_distance / TREND_STRENGTH_FULL)
            return "SELL", strength

    except (TypeError, ValueError, KeyError, IndexError):
        pass

    return "NO_TRADE", 0.0


def range_strategy(df):
    if df is None or len(df) < RANGE_LOOKBACK:
        return "NO_TRADE", 0.0

    try:
        closes = df["close"].iloc[-RANGE_LOOKBACK:]
        mean_price = closes.mean()
        std_price = closes.std()
        latest_close = closes.iloc[-1]

        if std_price <= 0:
            return "NO_TRADE", 0.0

        z_score = (latest_close - mean_price) / std_price

        if z_score <= -RANGE_ENTRY_Z:
            strength = min(1.0, abs(z_score) / 2.0)
            return "BUY", strength

        if z_score >= RANGE_ENTRY_Z:
            strength = min(1.0, abs(z_score) / 2.0)
            return "SELL", strength

    except (TypeError, ValueError, KeyError, IndexError, ZeroDivisionError):
        pass

    return "NO_TRADE", 0.0


def breakout_strategy(df):
    signal = detect_breakout(df)

    if signal in ("BUY", "SELL"):
        return signal, 1.0

    return "NO_TRADE", 0.0


def generate_signal(df, regime):
    """Return (BUY/SELL/NO_TRADE, signal_strength)."""
    if df is None or len(df) < 21:
        return "NO_TRADE", 0.0

    if regime in ("TRENDING_UP", "TRENDING_DOWN"):
        signal, strength = trend_strategy(df, regime)
        if signal != "NO_TRADE":
            return signal, strength

    if regime == "RANGING":
        signal, strength = range_strategy(df)
        if signal != "NO_TRADE":
            return signal, strength

    signal, strength = breakout_strategy(df)

    if signal != "NO_TRADE":
        return signal, strength

    return "NO_TRADE", 0.0
