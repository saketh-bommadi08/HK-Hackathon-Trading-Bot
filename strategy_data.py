import json
import math
import os
import tempfile
import time
from typing import Optional

from market_data import get_price, make_candle

DATA_DIR = os.getenv("ROOSTOO_DATA_DIR", os.path.dirname(os.path.abspath(__file__)))
CANDLE_FILE = os.path.join(DATA_DIR, "candles.json")

PAIR = "BTC/USD"

# Final strategy timeframe.
SAMPLE_INTERVAL = 5
CANDLE_DURATION = 60

MIN_VALID_SAMPLES = 3
MAX_CLOCK_DRIFT_SECONDS = 5


def _is_valid_candle(candle: object) -> bool:
    if not isinstance(candle, dict):
        return False

    required = ("timestamp", "open", "high", "low", "close")
    if any(key not in candle for key in required):
        return False

    try:
        timestamp = float(candle["timestamp"])
        values = [float(candle[key]) for key in required[1:]]
    except (TypeError, ValueError):
        return False

    if not math.isfinite(timestamp):
        return False

    if any(not math.isfinite(value) or value <= 0 for value in values):
        return False

    return (
        values[2] <= values[0] <= values[1]
        and values[2] <= values[3] <= values[1]
    )


def save_candles(candles: list[dict]) -> bool:
    valid = [candle for candle in candles if _is_valid_candle(candle)]

    directory = os.path.dirname(os.path.abspath(CANDLE_FILE))
    fd, temporary_path = tempfile.mkstemp(
        prefix=".candles_",
        suffix=".json",
        dir=directory,
        text=True,
    )

    try:
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            json.dump(valid, file, separators=(",", ":"))

        os.replace(temporary_path, CANDLE_FILE)
        return True

    except (OSError, TypeError, ValueError) as exc:
        print(f"[WARN] Could not save candles: {exc}")
        try:
            os.remove(temporary_path)
        except OSError:
            pass
        return False


def load_candles() -> list[dict]:
    if not os.path.exists(CANDLE_FILE):
        return []

    try:
        with open(CANDLE_FILE, "r", encoding="utf-8") as file:
            raw = json.load(file)

        if not isinstance(raw, list):
            print("[WARN] candles.json is not a list. Starting with empty history.")
            return []

        candles = [candle for candle in raw if _is_valid_candle(candle)]
        candles.sort(key=lambda candle: candle["timestamp"])

        # Remove duplicate timestamps.
        deduplicated = []
        seen = set()

        for candle in candles:
            timestamp = int(candle["timestamp"])
            if timestamp in seen:
                continue
            seen.add(timestamp)
            deduplicated.append(candle)

        if len(deduplicated) >= 2:
            gaps = [
                deduplicated[i]["timestamp"] - deduplicated[i - 1]["timestamp"]
                for i in range(1, len(deduplicated))
            ]

            # Development 10-second candles must not be mixed into the
            # final 60-second strategy history.
            if any(abs(gap - CANDLE_DURATION) > MAX_CLOCK_DRIFT_SECONDS for gap in gaps):
                print(
                    "[WARN] Existing candle history is not 1-minute data. "
                    "Ignoring it and starting fresh."
                )
                return []

        return deduplicated

    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(f"[WARN] Could not load candles.json: {exc}")
        return []


def collect_one_candle() -> Optional[dict]:
    prices = []
    start_time = time.time()
    deadline = start_time + CANDLE_DURATION

    while time.time() < deadline:
        price = get_price(PAIR)

        if price is not None:
            prices.append(price)
            print(f"[DATA] Price: {price}")

        remaining = deadline - time.time()
        if remaining <= 0:
            break

        time.sleep(min(SAMPLE_INTERVAL, remaining))

    if len(prices) < MIN_VALID_SAMPLES:
        print(
            f"[WARN] Candle discarded: only {len(prices)} valid samples "
            f"(minimum {MIN_VALID_SAMPLES})."
        )
        return None

    candle = make_candle(prices, int(start_time))

    if candle is None:
        print("[WARN] Candle discarded: could not construct valid OHLC.")
        return None

    print(
        f"[DATA] Candle complete | O={candle['open']} "
        f"H={candle['high']} L={candle['low']} C={candle['close']}"
    )

    return candle
