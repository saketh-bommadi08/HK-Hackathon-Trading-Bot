import math


def calculate_drawdown(current_equity, peak_equity):
    try:
        current_equity = float(current_equity)
        peak_equity = float(peak_equity)
    except (TypeError, ValueError):
        return None

    if (
        peak_equity <= 0
        or not math.isfinite(current_equity)
        or not math.isfinite(peak_equity)
    ):
        return None

    return max(0.0, (peak_equity - current_equity) / peak_equity)


def get_risk_multiplier(drawdown):
    if drawdown is None:
        return 0.0

    if drawdown < 0.03:
        return 1.0

    if drawdown < 0.06:
        return 0.5

    if drawdown < 0.10:
        return 0.25

    return 0.0
