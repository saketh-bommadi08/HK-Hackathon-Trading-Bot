import math
import time

from api_utils import sync_server_time
from config import DRY_RUN, PAIR
from decision import make_decision
from exchange_info import DEFAULT_RULES, get_pair_rules
from execution import execute_decision, reconcile_unknown_order
from orders import get_pending_count
from exit_logic import should_exit
from indicators import calculate_indicators
from portfolio import calculate_equity, get_portfolio_state
from regime import detect_regime
from state import load_state, save_state
from strategy import generate_signal
from strategy_data import (
    MAX_CLOCK_DRIFT_SECONDS,
    collect_one_candle,
    load_candles,
    save_candles,
)

MAX_CANDLES = 200
STARTING_CASH = 50000.0
MARKET_FEE = 0.001
LOOP_PAUSE = 1.0


def _safe_float(value):
    try:
        value = float(value)
        if math.isfinite(value):
            return value
    except (TypeError, ValueError):
        pass
    return None


def _get_rules():
    rules = get_pair_rules(PAIR)

    if rules is None:
        print("[WARN] Could not retrieve exchange rules. Using conservative defaults.")
        return dict(DEFAULT_RULES)

    if not rules["CanTrade"]:
        print(f"[WARN] {PAIR} is currently marked non-tradable.")

    return rules


def _validate_candle_spacing(candles):
    if len(candles) < 2:
        return True

    previous = candles[-2]["timestamp"]
    current = candles[-1]["timestamp"]
    gap = current - previous

    return abs(gap - 60) <= MAX_CLOCK_DRIFT_SECONDS


def _paper_update_after_fill(
    result,
    paper_cash,
    paper_position,
    entry_price,
    price,
):
    if result.get("Status") != "DRY_RUN":
        return paper_cash, paper_position, entry_price

    side = result.get("Side")
    quantity = _safe_float(result.get("Quantity"))

    if quantity is None or quantity <= 0:
        return paper_cash, paper_position, entry_price

    if side == "BUY":
        cost = quantity * price
        fee = cost * MARKET_FEE
        total_cost = cost + fee

        if total_cost > paper_cash:
            print("[WARN] Dry-run fill rejected locally: insufficient paper cash.")
            return paper_cash, paper_position, entry_price

        paper_cash -= total_cost
        paper_position += quantity
        entry_price = price

    elif side == "SELL":
        quantity = min(quantity, paper_position)
        proceeds = quantity * price
        fee = proceeds * MARKET_FEE

        paper_position -= quantity
        paper_cash += proceeds - fee

        if paper_position <= 1e-10:
            paper_position = 0.0
            entry_price = None

    return paper_cash, paper_position, entry_price


def main():
    print("=" * 60)
    print("HK HACKATHON — ROOSTOO TEST BOT")
    print("=" * 60)
    print(f"Pair: {PAIR}")
    print(f"Dry run: {DRY_RUN}")
    print("Strategy timeframe: 1-minute candles")
    print("=" * 60)

    if not sync_server_time():
        print("[WARN] Server time could not be synchronized.")
        print("[WARN] Signed requests may fail until time synchronization succeeds.")

    rules = _get_rules()

    candles = load_candles()
    state = load_state()

    print(f"[INFO] Loaded valid candles: {len(candles)}")

    # Development history and stale internal state should not be trusted blindly.
    paper_cash = STARTING_CASH
    paper_position = 0.0
    entry_price = None
    peak_equity = STARTING_CASH

    # In real TEST execution, account state is reconciled after a valid
    # live market price is available. Do not value an existing BTC position
    # using an artificial startup price.
    if not DRY_RUN:
        paper_cash = None
        paper_position = None
        peak_equity = state.get("peak_equity")

    # The first candle after startup/restart is a session boundary. It may be
    # separated from persisted historical data by an arbitrary amount of time.
    live_session_started = False

    cycle_number = 0

    while True:
        cycle_number += 1
        print("\n" + "-" * 60)
        print(f"[CYCLE {cycle_number}] Collecting 1-minute candle...")

        try:
            candle = collect_one_candle()

            if candle is None:
                print("[WARN] No valid candle this cycle. No trade.")
                time.sleep(LOOP_PAUSE)
                continue

            if not live_session_started:
                candles.append(candle)
                live_session_started = True
                print("[INFO] Live candle session started.")
            else:
                candles.append(candle)

                if not _validate_candle_spacing(candles):
                    print("[WARN] Candle spacing is not 1 minute. Discarding candle.")
                    candles.pop()
                    continue

            if len(candles) > MAX_CANDLES:
                candles.pop(0)

            if not save_candles(candles):
                print("[WARN] Candle persistence failed. Skipping strategy cycle.")
                continue

            if len(candles) < 21:
                print(f"[INFO] Waiting for history: {len(candles)}/21 candles.")
                continue

            df = calculate_indicators(candles)

            if df is None:
                print("[WARN] Indicator calculation invalid. NO_TRADE.")
                continue

            latest = df.iloc[-1]

            price = _safe_float(latest["close"])
            volatility = _safe_float(latest["volatility"])

            if price is None or price <= 0 or volatility is None or volatility <= 0:
                print("[WARN] Invalid market inputs. NO_TRADE.")
                continue

            regime = detect_regime(df)
            signal, signal_strength = generate_signal(df, regime)

            print(
                f"[SIGNAL] Price={price:.2f} | "
                f"Regime={regime} | "
                f"Signal={signal} | "
                f"Strength={signal_strength:.3f}"
            )

            # For real TEST execution, never generate a new order while an
            # exchange order is still pending.
            if not DRY_RUN:
                pending_count = get_pending_count()

                if pending_count is None:
                    print("[WARN] Pending-order state unavailable. NO_TRADE.")
                    continue

                if pending_count > 0:
                    print(f"[INFO] {pending_count} pending order(s). Waiting for resolution.")
                    continue

            # For real TEST execution, refresh the actual account before deciding.
            if not DRY_RUN:
                account_state = get_portfolio_state(price, PAIR)

                if account_state is None:
                    print("[WARN] Account state unavailable. NO_TRADE.")
                    continue

                paper_cash = account_state["cash"]
                paper_position = account_state["asset_quantity"]
                paper_equity = account_state["equity"]

                if paper_position <= 0:
                    entry_price = None
                elif entry_price is None:
                    print(
                        "[WARN] Existing exchange position has no known entry price. "
                        "Refusing new trade until state is reconciled."
                    )
                    continue
            else:
                paper_equity = calculate_equity(
                    paper_cash,
                    paper_position,
                    price,
                )

            if paper_equity is None:
                print("[WARN] Equity calculation failed. NO_TRADE.")
                continue

            if paper_equity > peak_equity:
                peak_equity = paper_equity

            if paper_position > 0 and entry_price is not None:
                if should_exit(
                    paper_position,
                    entry_price,
                    price,
                    signal,
                ):
                    signal = "SELL"
                    signal_strength = 1.0
                    print("[RISK] Exit condition triggered.")

            decision = make_decision(
                balance=paper_cash,
                price=price,
                volatility=volatility,
                signal=signal,
                signal_strength=signal_strength,
                current_equity=paper_equity,
                peak_equity=peak_equity,
                current_position=paper_position,
            )

            print(
                f"[DECISION] {decision['signal']} "
                f"| Qty={decision['quantity']:.8f} "
                f"| Reason={decision.get('reason', '')}"
            )

            result = execute_decision(
                decision=decision,
                pair=PAIR,
                price=price,
                current_position=paper_position,
                amount_precision=rules["AmountPrecision"],
                price_precision=rules["PricePrecision"],
                mini_order=rules["MiniOrder"],
            )

            print(f"[EXECUTION] {result}")

            if result.get("ReconcileRequired"):
                print(
                    "[CRITICAL] Order outcome is UNKNOWN. "
                    "No new order will be submitted automatically."
                )

                matches = reconcile_unknown_order(
                    PAIR,
                    result.get("Side"),
                    result.get("Quantity"),
                )

                if matches:
                    print(
                        "[CRITICAL] Possible matching orders found. "
                        "Manual/state reconciliation required before trading resumes."
                    )
                    for match in matches[:5]:
                        print(f"[CRITICAL] {match}")

                # Fail closed: do not continue autonomous trading with unknown state.
                print("[FATAL] Stopping bot to prevent duplicate trading.")
                return

            if result.get("Success") and result.get("Status") == "DRY_RUN":
                paper_cash, paper_position, entry_price = _paper_update_after_fill(
                    result,
                    paper_cash,
                    paper_position,
                    entry_price,
                    price,
                )

            elif (
                result.get("Success")
                and result.get("OrderDetail")
            ):
                order_detail = result["OrderDetail"]
                status = order_detail.get("Status")
                filled_quantity = _safe_float(
                    order_detail.get("FilledQuantity", 0)
                )

                if status == "FILLED":
                    if result.get("Side") == "BUY":
                        entry_price = _safe_float(
                            order_detail.get("FilledAverPrice")
                        ) or price
                    elif result.get("Side") == "SELL":
                        entry_price = None

                    state["last_order_id"] = order_detail.get("OrderID")
                    state["last_order_status"] = status

                elif status == "PENDING":
                    print(
                        "[WARN] Order is pending. "
                        "Autonomous state will not pretend it is filled."
                    )
                    state["last_order_id"] = order_detail.get("OrderID")
                    state["last_order_status"] = status

            state["position"] = paper_position
            state["entry_price"] = entry_price
            state["peak_equity"] = peak_equity

            if not save_state(state):
                print("[WARN] Could not persist bot state.")

        except KeyboardInterrupt:
            print("\n[INFO] Bot stopped by user.")
            return

        except Exception as exc:
            # Last-resort guard: an unexpected bug in one cycle should not
            # immediately kill the overnight process. The next cycle starts
            # from persisted state.
            print(f"[ERROR] Unexpected cycle error: {type(exc).__name__}: {exc}")
            print("[INFO] Skipping this cycle. No trade will be attempted.")

        time.sleep(LOOP_PAUSE)


if __name__ == "__main__":
    main()
