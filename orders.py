from typing import Optional

from api_utils import signed_post


def query_order(
    pair: Optional[str] = None,
    order_id: Optional[int | str] = None,
    pending_only: Optional[bool] = None,
    limit: Optional[int] = None,
):
    if order_id is not None:
        params = {"order_id": str(order_id)}
    else:
        params = {}

        if pair is not None:
            params["pair"] = pair

        if pending_only is not None:
            params["pending_only"] = "TRUE" if pending_only else "FALSE"

        if limit is not None:
            params["limit"] = str(limit)

    data, error = signed_post("/v3/query_order", params)

    if error is not None:
        return {
            "Success": False,
            "ErrMsg": f"Query order failed: {error}",
            "Status": "UNKNOWN",
        }

    return data


def get_order_by_id(pair: str, order_id: int | str):
    return query_order(order_id=order_id)


def cancel_order(
    pair: Optional[str] = None,
    order_id: Optional[int | str] = None,
):
    if order_id is not None:
        params = {"order_id": str(order_id)}
    elif pair is not None:
        params = {"pair": pair}
    else:
        return {
            "Success": False,
            "ErrMsg": "Refusing to cancel all pending orders without an explicit pair/order_id.",
        }

    data, error = signed_post("/v3/cancel_order", params)

    if error is not None:
        return {
            "Success": False,
            "ErrMsg": f"Cancel order failed: {error}",
            "Status": "UNKNOWN",
        }

    return data


def get_pending_count():
    from api_utils import signed_get

    data = signed_get("/v3/pending_count", {})

    if data is None:
        return None

    # Roostoo can return Success=False when there are no pending orders.
    if data.get("Success") is False and data.get("TotalPending") != 0:
        print(f"[WARN] Pending-order request failed: {data.get('ErrMsg', 'unknown error')}")
        return None

    try:
        count = int(data.get("TotalPending", 0))
    except (TypeError, ValueError):
        return None

    return max(0, count)
