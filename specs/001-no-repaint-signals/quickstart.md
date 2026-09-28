# Quickstart / Validation Guide: Eliminate Signal Repaint

## Run the tests

```bash
cd app
pip install -r requirements-dev.txt
pytest ../tests/data/test_manager.py -v
```

Expected: all cases pass, including the parametrized cases across `candle_period` values (`4h`,
`1d`) and the "already closed, no trim" / "short history" edge cases from the spec.

## Manual validation (matches spec User Story 1, Acceptance Scenario 2)

1. Start the bot normally (`docker compose up --build`, or `python app.py` locally) against a
   `config.yml` with at least one indicator on a short `update_interval` (e.g. 300s) and a
   `candle_period` that is *not* aligned to run every cycle (e.g. `4h`).
2. Let two consecutive analysis cycles run without a `4h` candle boundary passing between them
   (i.e., both cycles land inside the same still-open 4h candle).
3. Compare the logged/notified indicator values (RSI, etc.) for the same pair between the two
   cycles.
4. **Before this fix**: values could differ between the two cycles (the open candle's OHLC moves as
   the market moves). **After this fix**: values are identical, because both cycles used the same
   most-recent *closed* candle as their latest data point.

## Regression check for existing config compatibility (User Story 2)

1. Use a `config.yml` from before this change (or `config-clean.yml` as a stand-in).
2. Confirm the bot starts and completes one full cycle with no new required fields and no errors.
3. Confirm a Telegram (or stdout/webhook) notification is produced with the same fields as before.
