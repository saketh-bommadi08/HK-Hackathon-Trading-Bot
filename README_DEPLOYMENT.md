# HK Hackathon — Roostoo TEST Deployment Package

## Scope

This package is a hardening pass over the existing HK Hackathon bot.

The strategy architecture is intentionally preserved:

MARKET DATA
→ REGIME
→ TREND / RANGE / BREAKOUT
→ SIGNAL STRENGTH
→ POSITION SIZING
→ DRAWDOWN RISK
→ EXECUTION
→ STATE

No AI/ML/LLM/RL, no exchange simulator, and no strategy-family redesign were added.

## Important

`config.py` ships with placeholder credentials and:

```python
DRY_RUN = True
```

Do not enable actual TEST order submission until the execution/reconciliation flow has been explicitly verified.

The API base URL is:

`https://mock-api.roostoo.com`

## Files

- `bot.py` — main control loop
- `config.py` — local credentials/configuration
- `api_utils.py` — common HTTP/signing/error handling
- `market_data.py` — ticker retrieval and price validation
- `strategy_data.py` — 1-minute candle collection/persistence
- `indicators.py` — EMA/volatility calculations
- `regime.py` — market regime classification
- `strategy.py` — trend/range/breakout signal generation
- `breakout.py` — breakout detector
- `risk.py` — position sizing/exposure
- `drawdown.py` — drawdown governor
- `decision.py` — strategy-to-order decision
- `execution.py` — order validation/submission
- `orders.py` — query/cancel order operations
- `account.py` — balance/wallet access
- `exchange_info.py` — dynamic pair rules
- `portfolio.py` — account/portfolio calculations
- `exit_logic.py` — exit conditions
- `state.py` — atomic persistent bot state
- `candles.json` — generated at runtime
- `bot_state.json` — generated at runtime
- `CHANGELOG_HARDENING.md` — detailed change record

## Before first deployment

1. Install dependencies:
   `pip install -r requirements.txt`

2. Put the TEST credentials into `config.py`.

3. Keep `DRY_RUN = True` initially.

4. Remove any old development `candles.json` and `bot_state.json`.

5. Run the bot long enough to collect at least 21 proper one-minute candles.

6. Confirm:
   - ticker failures do not crash the process
   - malformed data results in NO_TRADE
   - 1-minute candle spacing is maintained
   - no strategy decision occurs before 21 candles

7. Only after the order path is verified should `DRY_RUN` be changed for the Roostoo mock/test environment.

8. If an order submission returns `Status="UNKNOWN"` or `ReconcileRequired=True`, the bot deliberately stops. Do not submit another order until the exchange state is reconciled.

## Strategy note

This package does not claim that the strategy is profitable. Its purpose is to make the existing strategy safe enough to observe and evaluate.

The backtester remains the correct tool for deciding whether the adaptive strategy actually improves on the EMA baseline.
