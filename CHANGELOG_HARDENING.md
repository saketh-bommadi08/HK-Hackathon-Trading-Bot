# Hardening Change Log

## 1. Market-data resilience

### Before

A connection reset such as:

`ConnectionResetError: [WinError 10054]`

could propagate through:

`get_ticker → get_price → collect_one_candle → main`

and terminate the bot.

### After

Ticker requests are isolated behind `api_utils.public_get()`.

Handled cases include:

- connection errors
- timeouts
- HTTP errors
- invalid JSON
- non-object JSON
- missing `Data`
- missing pair
- missing/invalid `LastPrice`
- non-finite prices
- non-positive prices

A failed ticker sample becomes a skipped sample.

The candle collector can therefore continue to the next scheduled sample.

---

## 2. 1-minute candle integrity

The final strategy timeframe is:

- sample every 5 seconds
- collect for 60 seconds
- require at least 3 valid samples

Invalid/empty candles are rejected.

Existing history is validated for approximately 60-second spacing. The old 10-second development candles are therefore not silently mixed into final strategy history.

Candle writes are atomic using a temporary file followed by `os.replace()`.

---

## 3. Indicator and strategy fail-safe behavior

Indicator calculation validates:

- required columns
- numeric data
- NaN values
- finite values
- positive close

Regime detection and strategy functions return `NO_TRADE` when their inputs are invalid instead of raising through the main loop.

This is intentionally conservative.

---

## 4. Risk engine hardening

The risk layer now rejects:

- invalid balances
- invalid prices
- invalid volatility
- invalid signal strength
- non-finite inputs

Invalid drawdown/equity state produces a zero risk multiplier.

The exposure limit remains 20% of available balance.

The base exposure remains 10% of available balance.

The existing volatility scaling and signal-strength scaling are preserved.

---

## 5. Exchange rules

`exchange_info.py` reads the current pair rules from `/v3/exchangeInfo`.

It supports both:

- documented `TradePairs[pair]` structure
- the directly returned pair object observed during development

The execution layer therefore does not permanently hardcode BTC/USD precision when exchange information is available.

Conservative defaults remain available if the endpoint cannot be reached.

---

## 6. Account handling

`account.py` safely handles balance failures.

Both observed wallet formats are accepted:

- `SpotWallet`
- `Wallet`

Unknown account state is represented as `None`, not as zero.

The bot therefore refuses to make an autonomous live/test decision when it cannot establish account state.

---

## 7. Server-time synchronization

Signed Roostoo requests require a millisecond timestamp within the server's accepted timing window.

`api_utils.py` synchronizes against `/v3/serverTime` and applies a local offset to generated signed timestamps.

The offset is refreshed periodically.

---

## 8. Signing

Signed parameters are sorted by key before HMAC SHA256 generation, matching the documented Roostoo signing procedure.

POST requests use:

`application/x-www-form-urlencoded`

as required by the API documentation.

---

## 9. Order query/cancel methods

`orders.py` uses:

- `POST /v3/query_order`
- `POST /v3/cancel_order`

The previous `GET /v3/query_order` implementation has been removed.

The documented parameter name `order_id` is used.

The cancel helper refuses to cancel all pending orders accidentally when neither a pair nor an order ID is supplied.

---

## 10. Order-submission uncertainty

This is the most important execution safeguard.

If `/v3/place_order` times out or the connection is reset, the bot does NOT automatically resend the order.

Why?

The exchange may have received and executed the original order even though the response never reached the bot.

The result is therefore marked:

`Status="UNKNOWN"`

and:

`ReconcileRequired=True`

The bot then queries order history for possible matching orders and stops autonomous trading rather than risking a duplicate.

---

## 11. Order lifecycle

The bot distinguishes at least:

- NO_TRADE
- DRY_RUN
- FILLED
- PENDING
- REJECTED
- FAILED
- UNKNOWN

A successful order submission is not treated as an automatic fill unless the API response says it is filled.

For filled orders, `FilledQuantity` and `FilledAverPrice` are used where available.

---

## 12. Position/state persistence

`state.py` atomically persists:

- position
- entry price
- peak equity
- last order ID
- last order status

This prevents a partially written JSON file from becoming the next startup state.

---

## 13. Startup account safety

In non-dry-run mode, the bot obtains account state before autonomous operation.

It refuses to trade when the account cannot be read.

If an exchange position exists without a known entry price, the bot refuses new autonomous decisions rather than inventing an entry price.

---

## 14. Main-loop resilience

The bot has a last-resort per-cycle exception guard.

An unexpected bug in one cycle therefore does not automatically terminate the entire process.

The cycle is skipped and persisted state remains available.

This is not a substitute for fixing exceptions; it is the final containment layer for overnight operation.

---

## 15. Strategy architecture deliberately unchanged

The following strategy design is preserved:

### Trending
EMA 9 / EMA 21 relationship plus price confirmation.

### Ranging
20-candle z-score mean reversion.

### Breakout
21-candle high/low breakout with a 0.05% price buffer.

### Risk
10% base exposure, volatility scaling, signal-strength scaling, 20% exposure cap.

### Drawdown governor
- below 3% → 1.0x
- 3–6% → 0.5x
- 6–10% → 0.25x
- 10%+ → 0x

### Exit
- strategy SELL
- approximately 1% adverse move from entry

No new indicator family or AI/ML component was introduced.

---

## 16. Deliberate non-changes

Not added:

- AI
- machine learning
- LLM
- reinforcement learning
- high-frequency execution
- market making
- arbitrage
- short positions
- large-scale strategy parameter optimization
- a new exchange simulator

These remain outside the locked project scope.

---

## 17. Known limitation before autonomous TEST deployment

The bot is deliberately conservative around restart reconciliation.

The Roostoo API does not provide a client-order-id mechanism in the documented order interface used here. Therefore, an ambiguous submission cannot be made perfectly idempotent by client ID.

The code handles this by:

1. never blindly retrying an uncertain order,
2. querying recent orders for possible matches,
3. stopping autonomous trading if the state remains uncertain.

This is safer than pretending an ambiguous request failed.

---

## 18. Testing philosophy

The hardening is designed for the following failure model:

API works
→ continue

API temporarily fails
→ skip/continue where safe

Account state unavailable
→ NO_TRADE

Market data malformed
→ NO_TRADE

Strategy inputs invalid
→ NO_TRADE

Order rejected
→ do not update position

Order pending
→ do not pretend filled

Order outcome unknown
→ reconcile and stop

Unexpected code error
→ skip current cycle

This is the intended fail-safe behavior for the overnight TEST run.


## 19. Pending-order guard

Before generating a new autonomous TEST order, the bot checks `/v3/pending_count`.

If the endpoint is unavailable, the bot does not trade.

If one or more orders are pending, the bot waits instead of submitting another order.
This prevents a still-open order from being mistaken for an absent position and avoids duplicate exposure.
