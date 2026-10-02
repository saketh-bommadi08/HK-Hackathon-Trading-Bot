import math


def calculate_position_size(balance, price, volatility, signal_strength=1.0):
    try:
        balance = float(balance)
        price = float(price)
        volatility = float(volatility)
        signal_strength = float(signal_strength)
    except (TypeError, ValueError):
        return 0.0

    if (
        balance <= 0
        or price <= 0
        or volatility <= 0
        or not math.isfinite(balance)
        or not math.isfinite(price)
        or not math.isfinite(volatility)
        or not math.isfinite(signal_strength)
    ):
        return 0.0

    signal_strength = max(0.0, min(signal_strength, 1.0))

    base_exposure = balance * 0.10

    volatility_factor = 0.01 / volatility
    volatility_factor = max(0.25, min(volatility_factor, 1.0))

    position_value = base_exposure * volatility_factor * signal_strength
    quantity = position_value / price

    if not math.isfinite(quantity) or quantity <= 0:
        return 0.0

    return quantity


def apply_exposure_limit(quantity, price, balance):
    try:
        quantity = float(quantity)
        price = float(price)
        balance = float(balance)
    except (TypeError, ValueError):
        return 0.0

    if quantity <= 0 or price <= 0 or balance <= 0:
        return 0.0

    max_exposure = balance * 0.20
    max_quantity = max_exposure / price

    return max(0.0, min(quantity, max_quantity))
