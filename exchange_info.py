import math
from typing import Optional

from api_utils import public_get


DEFAULT_RULES = {
    "CanTrade": True,
    "PricePrecision": 2,
    "AmountPrecision": 5,
    "MiniOrder": 1.0,
}


def get_pair_rules(pair: str) -> Optional[dict]:
    data = public_get("/v3/exchangeInfo")

    if data is None:
        return None

    if data.get("Success") is False:
        print(f"[WARN] exchangeInfo rejected: {data.get('ErrMsg', 'unknown error')}")
        return None

    # Current documented structure.
    trade_pairs = data.get("TradePairs")
    if isinstance(trade_pairs, dict):
        rules = trade_pairs.get(pair)
        if isinstance(rules, dict):
            return _normalize_rules(rules)

    # Some observed test responses return the pair object directly.
    if data.get("Coin") and data.get("Unit"):
        if f"{data.get('Coin')}/{data.get('Unit')}" == pair:
            return _normalize_rules(data)

    return None


def _normalize_rules(rules: dict) -> Optional[dict]:
    try:
        price_precision = int(rules["PricePrecision"])
        amount_precision = int(rules["AmountPrecision"])
        mini_order = float(rules["MiniOrder"])
        can_trade = bool(rules.get("CanTrade", False))

        if (
            price_precision < 0
            or amount_precision < 0
            or not math.isfinite(mini_order)
            or mini_order < 0
        ):
            return None

        return {
            "CanTrade": can_trade,
            "PricePrecision": price_precision,
            "AmountPrecision": amount_precision,
            "MiniOrder": mini_order,
        }

    except (KeyError, TypeError, ValueError):
        return None
