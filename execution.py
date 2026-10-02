import math
from typing import Optional

from api_utils import signed_post
from config import DRY_RUN
from orders import query_order


# These are conservative defaults. The bot also validates against exchangeInfo
# when available through bot.py.
DEFAULT_AMOUNT_PRECISION = 5
DEFAULT_PRICE_PRECISION = 2
DEFAULT_MIN_ORDER = 1.0


def _round_down(value: float, decimals: int) -> float:
    factor = 10 ** decimals
    return math.floor(value * factor + 1e-12) / factor


def validate_order(
    pair: str,
    side: str,
    quantity: float,
    price: float,
    amount_precision: int = DEFAULT_AMOUNT_PRECISION,
    price_precision: int = DEFAULT_PRICE_PRECISION,
    mini_order: float = DEFAULT_MIN_ORDER,
):
    if side not in ("BUY", "SELL"):
        return False, "Invalid side"

    try:
        quantity = float(quantity)
        price = float(price)
        mini_order = float(mini_order)
    except (TypeError, ValueError):
        return False, "Non-numeric order input"

    if (
        not math.isfinite(quantity)
        or not math.isfinite(price)
        or quantity <= 0
        or price <= 0
    ):
        return False, "Quantity and price must be positive finite values"

    rounded_quantity = round(quantity, amount_precision)

    if abs(rounded_quantity - quantity) > 1e-12:
        return False, "Quantity exceeds allowed precision"

    rounded_price = round(price, price_precision)

    if abs(rounded_price - price) > 1e-8:
        return False, "Price exceeds allowed precision"

    order_value = quantity * price

    if order_value <= mini_order:
        return False, f"Order value must be greater than MiniOrder ({mini_order})"

    return True, "Valid"


def place_order(
    pair: str,
    side: str,
    order_type: str,
    quantity: float,
    price: Optional[float] = None,
    amount_precision: int = DEFAULT_AMOUNT_PRECISION,
    price_precision: int = DEFAULT_PRICE_PRECISION,
    mini_order: float = DEFAULT_MIN_ORDER,
):
    quantity = round(float(quantity), amount_precision)

    if order_type == "LIMIT" and price is None:
        return {
            "Success": False,
            "ErrMsg": "LIMIT order requires price",
            "Status": "REJECTED",
        }

    params = {
        "pair": pair,
        "side": side,
        "type": order_type,
        "quantity": str(quantity),
    }

    if order_type == "LIMIT":
        params["price"] = str(round(float(price), price_precision))

    data, error = signed_post("/v3/place_order", params)

    if error == "NETWORK_UNKNOWN":
        # NEVER automatically submit another order after an uncertain outcome.
        return {
            "Success": False,
            "ErrMsg": "Order outcome is unknown after network failure.",
            "Status": "UNKNOWN",
            "ReconcileRequired": True,
            "Side": side,
            "Quantity": quantity,
            "Pair": pair,
        }

    if error is not None:
        return {
            "Success": False,
            "ErrMsg": f"Order request failed: {error}",
            "Status": "FAILED",
        }

    return data


def execute_decision(
    decision,
    pair,
    price,
    current_position,
    amount_precision=DEFAULT_AMOUNT_PRECISION,
    price_precision=DEFAULT_PRICE_PRECISION,
    mini_order=DEFAULT_MIN_ORDER,
):
    signal = decision.get("signal")
    quantity = decision.get("quantity", 0.0)

    if signal == "NO_TRADE":
        return {
            "Success": True,
            "Status": "NO_TRADE",
        }

    try:
        quantity = float(quantity)
        price = float(price)
        current_position = float(current_position)
    except (TypeError, ValueError):
        return {
            "Success": False,
            "ErrMsg": "Invalid execution inputs",
            "Status": "FAILED",
        }

    if signal == "BUY":
        if current_position > 0:
            return {
                "Success": True,
                "Status": "ALREADY_LONG",
            }
        side = "BUY"

    elif signal == "SELL":
        if current_position <= 0:
            return {
                "Success": True,
                "Status": "NO_POSITION",
            }
        side = "SELL"

        # Never sell more than the known long position.
        quantity = min(quantity, current_position)

    else:
        return {
            "Success": False,
            "ErrMsg": "Invalid signal",
            "Status": "FAILED",
        }

    quantity = round(quantity, amount_precision)

    if quantity <= 0:
        return {
            "Success": False,
            "ErrMsg": "Invalid order quantity",
            "Status": "FAILED",
        }

    valid, message = validate_order(
        pair,
        side,
        quantity,
        price,
        amount_precision=amount_precision,
        price_precision=price_precision,
        mini_order=mini_order,
    )

    if not valid:
        return {
            "Success": False,
            "ErrMsg": message,
            "Status": "REJECTED",
        }

    if DRY_RUN:
        return {
            "Success": True,
            "Status": "DRY_RUN",
            "Pair": pair,
            "Side": side,
            "Type": "MARKET",
            "Quantity": quantity,
        }

    return place_order(
        pair=pair,
        side=side,
        order_type="MARKET",
        quantity=quantity,
        amount_precision=amount_precision,
        price_precision=price_precision,
        mini_order=mini_order,
    )


def reconcile_unknown_order(pair: str, side: str, quantity: float):
    """
    Deliberately conservative.

    If a placement request timed out, we do not place another order.
    We query the pair's recent order history and return it to the caller
    for inspection/reconciliation.
    """
    response = query_order(pair=pair, pending_only=False, limit=100)

    if not response or response.get("Success") is False:
        return None

    matches = []
    for order in response.get("OrderMatched", []):
        try:
            same_side = order.get("Side") == side
            same_quantity = abs(float(order.get("Quantity", 0)) - float(quantity)) < 1e-10

            if same_side and same_quantity:
                matches.append(order)
        except (TypeError, ValueError):
            continue

    return matches
