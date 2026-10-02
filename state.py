import json
import os
import tempfile


DATA_DIR = os.getenv("ROOSTOO_DATA_DIR", os.path.dirname(os.path.abspath(__file__)))
STATE_FILE = os.path.join(DATA_DIR, "bot_state.json")


DEFAULT_STATE = {
    "entry_price": None,
    "peak_equity": None,
    "position": 0.0,
    "last_order_id": None,
    "last_order_status": None,
}


def load_state():
    if not os.path.exists(STATE_FILE):
        return dict(DEFAULT_STATE)

    try:
        with open(STATE_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        if not isinstance(data, dict):
            return dict(DEFAULT_STATE)

        state = dict(DEFAULT_STATE)
        state.update(data)
        return state

    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(f"[WARN] Could not load bot state: {exc}")
        return dict(DEFAULT_STATE)


def save_state(state):
    directory = os.path.dirname(os.path.abspath(STATE_FILE))
    fd, temporary_path = tempfile.mkstemp(
        prefix=".bot_state_",
        suffix=".json",
        dir=directory,
        text=True,
    )

    try:
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            json.dump(state, file, indent=2)

        os.replace(temporary_path, STATE_FILE)
        return True

    except (OSError, TypeError, ValueError) as exc:
        print(f"[WARN] Could not save bot state: {exc}")
        try:
            os.remove(temporary_path)
        except OSError:
            pass
        return False
