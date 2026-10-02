import math
import pandas as pd


def calculate_indicators(candles):
    if candles is None or len(candles) < 21:
        return None

    try:
        df = pd.DataFrame(candles)

        required = ["open", "high", "low", "close", "timestamp"]
        if any(column not in df.columns for column in required):
            return None

        for column in ["open", "high", "low", "close", "timestamp"]:
            df[column] = pd.to_numeric(df[column], errors="coerce")

        if df[required].isna().any().any():
            return None

        df["ema_9"] = df["close"].ewm(span=9, adjust=False).mean()
        df["ema_21"] = df["close"].ewm(span=21, adjust=False).mean()
        df["returns"] = df["close"].pct_change()
        df["volatility"] = df["returns"].rolling(20).std()

        latest = df.iloc[-1]
        for column in ["close", "ema_9", "ema_21", "volatility"]:
            value = latest[column]
            if pd.isna(value):
                return None
            if not math.isfinite(float(value)):
                return None

        if float(latest["close"]) <= 0:
            return None

        return df

    except (TypeError, ValueError, KeyError):
        return None
