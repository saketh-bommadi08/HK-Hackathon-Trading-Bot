import hashlib
import hmac
import time
from typing import Any, Dict, Optional
from urllib.parse import quote

import requests

from config import API_KEY, SECRET_KEY, BASE_URL

REQUEST_TIMEOUT = 10
SERVER_TIME_REFRESH_SECONDS = 3600

_server_time_offset_ms = 0
_last_server_time_sync = 0.0


def _safe_error_text(response: Optional[requests.Response]) -> str:
    if response is None:
        return ""
    try:
        text = response.text.strip()
        return text[:500]
    except Exception:
        return ""


def _request_timestamp_ms() -> int:
    return int(time.time() * 1000) + _server_time_offset_ms


def sync_server_time() -> bool:
    """Synchronize local timestamp generation with Roostoo server time."""
    global _server_time_offset_ms, _last_server_time_sync

    try:
        before = int(time.time() * 1000)
        response = requests.get(
            f"{BASE_URL}/v3/serverTime",
            timeout=REQUEST_TIMEOUT,
        )
        after = int(time.time() * 1000)
        response.raise_for_status()
        data = response.json()

        server_time = data.get("ServerTime")
        if not isinstance(server_time, (int, float)):
            print("[WARN] serverTime response did not contain a valid ServerTime.")
            return False

        local_midpoint = (before + after) // 2
        _server_time_offset_ms = int(server_time - local_midpoint)
        _last_server_time_sync = time.time()

        print(f"[INFO] Server time synchronized. Offset: {_server_time_offset_ms} ms")
        return True

    except (requests.RequestException, ValueError, TypeError) as exc:
        print(f"[WARN] Could not synchronize server time: {exc}")
        return False


def ensure_server_time_sync() -> bool:
    if time.time() - _last_server_time_sync >= SERVER_TIME_REFRESH_SECONDS:
        return sync_server_time()
    return True


def _timestamp() -> str:
    return str(_request_timestamp_ms())


def _signed_payload(payload: Dict[str, Any]) -> tuple[Dict[str, str], Dict[str, Any], str]:
    """
    Add timestamp and create the Roostoo HMAC SHA256 signature.

    Roostoo signs the sorted key=value parameter string.
    """
    payload = dict(payload)
    payload["timestamp"] = _timestamp()

    sorted_keys = sorted(payload.keys())
    total_params = "&".join(
        f"{key}={payload[key]}" for key in sorted_keys
    )

    signature = hmac.new(
        SECRET_KEY.encode("utf-8"),
        total_params.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    headers = {
        "RST-API-KEY": API_KEY,
        "MSG-SIGNATURE": signature,
    }

    return headers, payload, total_params


def public_get(path: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    try:
        response = requests.get(
            f"{BASE_URL}{path}",
            params=params,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()

        if not isinstance(data, dict):
            print(f"[WARN] {path}: API response was not a JSON object.")
            return None

        return data

    except requests.RequestException as exc:
        print(f"[WARN] {path}: request failed: {exc}")
    except ValueError:
        print(f"[WARN] {path}: API returned invalid JSON.")
    except Exception as exc:
        print(f"[WARN] {path}: unexpected error: {exc}")

    return None


def signed_get(
    path: str,
    params: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    ensure_server_time_sync()
    headers, payload, _ = _signed_payload(params or {})

    try:
        response = requests.get(
            f"{BASE_URL}{path}",
            params=payload,
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()

        if not isinstance(data, dict):
            print(f"[WARN] {path}: API response was not a JSON object.")
            return None

        return data

    except requests.RequestException as exc:
        print(f"[WARN] {path}: request failed: {exc}")
    except ValueError:
        print(f"[WARN] {path}: API returned invalid JSON.")
    except Exception as exc:
        print(f"[WARN] {path}: unexpected error: {exc}")

    return None


def signed_post(
    path: str,
    params: Optional[Dict[str, Any]] = None,
) -> tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Return (response_dict, error_kind).

    error_kind is None on a received JSON response.
    'NETWORK_UNKNOWN' means the request outcome is unknown and MUST NOT
    automatically be retried as a new order.
    """
    ensure_server_time_sync()
    headers, payload, total_params = _signed_payload(params or {})
    headers["Content-Type"] = "application/x-www-form-urlencoded"

    try:
        response = requests.post(
            f"{BASE_URL}{path}",
            data=total_params,
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()

        if not isinstance(data, dict):
            print(f"[WARN] {path}: API response was not a JSON object.")
            return None, "BAD_RESPONSE"

        return data, None

    except requests.Timeout as exc:
        print(f"[WARN] {path}: request timed out; outcome may be unknown: {exc}")
        return None, "NETWORK_UNKNOWN"
    except requests.ConnectionError as exc:
        print(f"[WARN] {path}: connection failed; outcome may be unknown: {exc}")
        return None, "NETWORK_UNKNOWN"
    except requests.RequestException as exc:
        print(f"[WARN] {path}: request failed: {exc}")
        return None, "REQUEST_FAILED"
    except ValueError:
        print(f"[WARN] {path}: API returned invalid JSON.")
        return None, "BAD_RESPONSE"
    except Exception as exc:
        print(f"[WARN] {path}: unexpected error: {exc}")
        return None, "UNKNOWN"
