import os

BASE_URL = os.getenv("ROOSTOO_BASE_URL", "https://mock-api.roostoo.com")
PAIR = os.getenv("ROOSTOO_PAIR", "BTC/USD")

# Safe default: the bot will NOT place orders unless explicitly disabled.
DRY_RUN = os.getenv("ROOSTOO_DRY_RUN", "true").strip().lower() in {
    "1", "true", "yes", "on"
}

API_KEY = os.getenv("ROOSTOO_API_KEY", "").strip()
SECRET_KEY = os.getenv("ROOSTOO_SECRET_KEY", "").strip()

if not DRY_RUN and (not API_KEY or not SECRET_KEY):
    raise RuntimeError(
        "ROOSTOO_API_KEY and ROOSTOO_SECRET_KEY must be set when DRY_RUN is false."
    )
