import math
from typing import Optional

from api_utils import public_get

BASE_URL = "https://mock-api.roostoo.com"
PAIR = "BTC/USD"


def get_ticker(pair: str) -> Optional[dict]:
    data = public_get(
        "/v3/ticker",
        params={"timestamp": __import__("time").time_ns() // 1_000_000, "pair": pair},
    )

    if data is None:
        return None

    if data.get("Success") is False:
        print(f"[WARN] Ticker API rejected request: {data.get('ErrMsg', 'unknown error')}")
        return None

    ticker_data = data.get("Data")
    if not isinstance(ticker_data, dict):
        print("[WARN] Ticker response has no valid Data object.")
        return None

    ticker = ticker_data.get(pair)
    if not isinstance(ticker, dict):
        print(f"[WARN] Ticker response does not contain {pair}.")
        return None

    last_price = ticker.get("LastPrice")
    if not isinstance(last_price, (int, float)) or not math.isfinite(float(last_price)):
        print(f"[WARN] Invalid LastPrice for {pair}: {last_price!r}")
        return None

    if float(last_price) <= 0:
        print(f"[WARN] Non-positive LastPrice for {pair}: {last_price!r}")
        return None

    return ticker


def get_price(pair: str) -> Optional[float]:
    ticker = get_ticker(pair)

    if ticker is None:
        return None

    return float(ticker["LastPrice"])


def make_candle(prices: list[float], timestamp: int) -> Optional[dict]:
    if not prices:
        return None

    valid_prices = [
        float(price)
        for price in prices
        if isinstance(price, (int, float))
        and math.isfinite(float(price))
        and float(price) > 0
    ]

    if not valid_prices:
        return None

    return {
        "timestamp": int(timestamp),
        "open": valid_prices[0],
        "high": max(valid_prices),
        "low": min(valid_prices),
        "close": valid_prices[-1],
    }
