import math

from risk import calculate_position_size, apply_exposure_limit
from drawdown import calculate_drawdown, get_risk_multiplier


def make_decision(
    balance,
    price,
    volatility,
    signal,
    signal_strength,
    current_equity,
    peak_equity,
    current_position,
):
    drawdown = calculate_drawdown(current_equity, peak_equity)

    if drawdown is None:
        return {
            "signal": "NO_TRADE",
            "quantity": 0.0,
            "drawdown": None,
            "reason": "Invalid equity state",
        }

    risk_multiplier = get_risk_multiplier(drawdown)

    if signal == "NO_TRADE":
        return {
            "signal": "NO_TRADE",
            "quantity": 0.0,
            "drawdown": drawdown,
            "reason": "Strategy says no trade",
        }

    try:
        current_position = float(current_position)
        price = float(price)
        volatility = float(volatility)
        signal_strength = float(signal_strength)
        balance = float(balance)
    except (TypeError, ValueError):
        return {
            "signal": "NO_TRADE",
            "quantity": 0.0,
            "drawdown": drawdown,
            "reason": "Invalid decision inputs",
        }

    if (
        balance <= 0
        or price <= 0
        or volatility <= 0
        or current_position < 0
        or not math.isfinite(balance)
        or not math.isfinite(price)
        or not math.isfinite(volatility)
        or not math.isfinite(signal_strength)
    ):
        return {
            "signal": "NO_TRADE",
            "quantity": 0.0,
            "drawdown": drawdown,
            "reason": "Unsafe decision inputs",
        }

    if signal == "SELL":
        if current_position <= 0:
            return {
                "signal": "NO_TRADE",
                "quantity": 0.0,
                "drawdown": drawdown,
                "reason": "No long position to sell",
            }

        return {
            "signal": "SELL",
            "quantity": current_position,
            "drawdown": drawdown,
            "reason": "Exit signal",
        }

    if signal == "BUY":
        if current_position > 0:
            return {
                "signal": "NO_TRADE",
                "quantity": 0.0,
                "drawdown": drawdown,
                "reason": "Already long",
            }

        if risk_multiplier <= 0:
            return {
                "signal": "NO_TRADE",
                "quantity": 0.0,
                "drawdown": drawdown,
                "reason": "Drawdown governor is defensive/flat",
            }

        quantity = calculate_position_size(
            balance,
            price,
            volatility,
            signal_strength,
        )
        quantity *= risk_multiplier

        quantity = apply_exposure_limit(
            quantity,
            price,
            balance,
        )

        if quantity <= 0:
            return {
                "signal": "NO_TRADE",
                "quantity": 0.0,
                "drawdown": drawdown,
                "reason": "Position size is zero",
            }

        return {
            "signal": "BUY",
            "quantity": quantity,
            "drawdown": drawdown,
            "reason": "Entry signal",
        }

    return {
        "signal": "NO_TRADE",
        "quantity": 0.0,
        "drawdown": drawdown,
        "reason": "Unknown signal",
    }
