"""
Local smoke checks. This script does not place orders.
"""

from breakout import detect_breakout
from decision import make_decision
from drawdown import calculate_drawdown, get_risk_multiplier
from execution import validate_order
from indicators import calculate_indicators
from regime import detect_regime
from risk import calculate_position_size
from strategy import generate_signal


def main():
    candles = []

    price = 100.0

    for i in range(25):
        candles.append({
            "timestamp": i * 60,
            "open": price,
            "high": price + 1,
            "low": price - 1,
            "close": price,
        })
        price += 0.1

    df = calculate_indicators(candles)

    assert df is not None
    assert detect_regime(df) in {
        "TRENDING_UP",
        "TRENDING_DOWN",
        "RANGING",
        "NO_TRADE",
    }

    signal, strength = generate_signal(df, detect_regime(df))
    assert signal in {"BUY", "SELL", "NO_TRADE"}
    assert 0.0 <= strength <= 1.0

    assert calculate_drawdown(100, 100) == 0.0
    assert get_risk_multiplier(0.02) == 1.0
    assert get_risk_multiplier(0.11) == 0.0

    qty = calculate_position_size(50000, 100, 0.01, 1.0)
    assert qty > 0

    decision = make_decision(
        balance=50000,
        price=100,
        volatility=0.01,
        signal="BUY",
        signal_strength=1.0,
        current_equity=50000,
        peak_equity=50000,
        current_position=0,
    )
    assert decision["signal"] == "BUY"
    assert decision["quantity"] > 0

    valid, _ = validate_order(
        "BTC/USD",
        "BUY",
        1.0,
        100.0,
        amount_precision=5,
        price_precision=2,
        mini_order=1.0,
    )
    assert valid

    invalid, _ = validate_order(
        "BTC/USD",
        "BUY",
        0.001,
        100.0,
        amount_precision=5,
        price_precision=2,
        mini_order=1.0,
    )
    assert not invalid

    print("ALL LOCAL SMOKE CHECKS PASSED")
    print("No API requests or orders were made.")


if __name__ == "__main__":
    main()
