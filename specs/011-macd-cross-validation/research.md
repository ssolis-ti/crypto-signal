# Phase 0 Research: Historical Validation of the SignalEnhancer Score for macd_cross

All decisions from `specs/007-signal-enhancer-validation/research.md` apply unchanged (in-process
reconstruction of context, real-instance scoring, basket-as-market-proxy sentiment, permutation-test
significance, pre-declared 24h/72h horizons). Only the trigger-detection decision is new:

## Decision: Replicate `MACDCross.analyze`'s exact cross condition and its `-2`/`dropna(how='all')` subtlety

**Rationale**: Reading `app/analyzers/indicators/macd_cross.py` line by line:

```python
macd_cross.dropna(how='all', inplace=True)
previous_macd, previous_signal = macd_cross.iloc[-2]['macd'], macd_cross.iloc[-2]['signal']
current_macd, current_signal = macd_cross.iloc[-1]['macd'], macd_cross.iloc[-1]['signal']
is_hot = previous_macd < previous_signal and current_macd > current_signal
is_cold = previous_macd > previous_signal and current_macd < current_signal
```

Two details matter for a faithful backtest replay, not an approximation:

1. `dropna(how='all')` drops a row only if **every** column (OHLCV + macd + signal) is NaN — during
   MACD's 33-candle warm-up (26 slow period + 9 signal period - 2), `macd`/`signal` are NaN but OHLCV
   columns are not, so `how='all'` does **not** drop those rows. The live indicator's `-2`/`-1`
   comparison is therefore only meaningful once both `iloc[-2]` and `iloc[-1]` land past the warm-up
   window — replaying this in the backtest means only evaluating the cross condition once
   `talib.MACD`'s own output is non-NaN at both `i-1` and `i`, which is the same warm-up gate `NaN`
   comparisons in Python naturally enforce (`NaN < NaN` is always `False`), so no special-casing is
   needed beyond checking both values are non-NaN before testing the cross.
2. The live indicator only ever checks **the single most recent candle** (`iloc[-1]` vs `iloc[-2]`)
   once per cycle — it does not scan history for crosses. Replaying this as "one event per historical
   candle where this same pairwise condition holds true" (scanning `i` from the first valid MACD value
   to the end) is the correct historical equivalent of "this condition would have been true had the
   bot run at that candle," consistent with how slice 007 replayed the RSI threshold-crossing trigger.

**Alternatives considered**: Approximating with a simpler "MACD histogram changes sign" check —
rejected: histogram sign change and line-crosses-signal are mathematically identical
(`histogram = macd - signal`, so `histogram` changes sign exactly when `macd` crosses `signal`), so
this isn't a real alternative, just a different implementation of the same condition; using the
histogram-sign-change form directly in the backtest script is simpler code and was adopted for that
reason, not as an approximation.
