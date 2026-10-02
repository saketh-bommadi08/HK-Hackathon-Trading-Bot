import math
from typing import Optional

from account import get_wallet


def calculate_equity(cash, asset_quantity, price):
    try:
        cash = float(cash)
        asset_quantity = float(asset_quantity)
        price = float(price)
    except (TypeError, ValueError):
        return None

    if not all(math.isfinite(value) for value in (cash, asset_quantity, price)):
        return None

    return cash + asset_quantity * price


def calculate_exposure(asset_quantity, price, equity):
    try:
        asset_quantity = float(asset_quantity)
        price = float(price)
        equity = float(equity)
    except (TypeError, ValueError):
        return None

    if equity <= 0 or asset_quantity < 0 or price <= 0:
        return None

    return (asset_quantity * price) / equity


def update_peak_equity(current_equity, peak_equity):
    if current_equity is None or peak_equity is None:
        return None

    return max(float(current_equity), float(peak_equity))


def get_account_balance():
    wallet = get_wallet()

    if wallet is None:
        return None

    return wallet


def get_free_balance(wallet, asset):
    if wallet is None:
        return None

    entry = wallet.get(asset)

    if not isinstance(entry, dict):
        return None

    try:
        value = float(entry.get("Free"))
    except (TypeError, ValueError):
        return None

    return value if value >= 0 else None


def get_portfolio_state(price, pair="BTC/USD"):
    wallet = get_wallet()

    if wallet is None:
        return None

    coin = pair.split("/")[0]
    unit = pair.split("/")[1]

    cash = get_free_balance(wallet, unit)
    asset_quantity = get_free_balance(wallet, coin)

    if cash is None or asset_quantity is None:
        return None

    equity = calculate_equity(cash, asset_quantity, price)
    exposure = calculate_exposure(asset_quantity, price, equity)

    if equity is None or exposure is None:
        return None

    return {
        "cash": cash,
        "asset_quantity": asset_quantity,
        "equity": equity,
        "exposure": exposure,
    }
