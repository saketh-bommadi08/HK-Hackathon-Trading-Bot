from typing import Optional

from api_utils import signed_get


def get_balance() -> Optional[dict]:
    return signed_get("/v3/balance", {})


def get_wallet() -> Optional[dict]:
    data = get_balance()

    if data is None:
        return None

    if data.get("Success") is False:
        print(f"[WARN] Balance API rejected request: {data.get('ErrMsg', 'unknown error')}")
        return None

    # Different Roostoo responses/docs have used different wallet keys.
    wallet = data.get("SpotWallet")
    if isinstance(wallet, dict):
        return wallet

    wallet = data.get("Wallet")
    if isinstance(wallet, dict):
        return wallet

    print("[WARN] Balance response contained no recognized wallet object.")
    return None


def get_free_balance(asset: str) -> Optional[float]:
    wallet = get_wallet()

    if wallet is None:
        return None

    entry = wallet.get(asset)
    if not isinstance(entry, dict):
        return None

    try:
        free = float(entry.get("Free"))
    except (TypeError, ValueError):
        return None

    if free < 0:
        return None

    return free
