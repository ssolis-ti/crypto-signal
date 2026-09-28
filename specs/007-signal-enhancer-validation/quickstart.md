# Quickstart / Validation Guide: SignalEnhancer Backtest (Slice 007)

## Run the backtest script

Requires network access to Binance's public REST API (read-only `fetch_ohlcv`).

```bash
docker run --rm \
  -v "$(pwd):/work" \
  -w /work \
  crypto-signal:dev \
  sh -c "PYTHONPATH=/work/app python specs/007-signal-enhancer-validation/validate_signal_enhancer.py"
```

On Windows/Git Bash, use the literal path form established in prior slices:

```bash
MSYS_NO_PATHCONV=1 docker run --rm -v "C:\Users\Proyecto Z\Desktop\deploy:/work" -w /work \
  crypto-signal:dev sh -c "PYTHONPATH=/work/app python specs/007-signal-enhancer-validation/validate_signal_enhancer.py"
```

The script prints its full results to stdout; those results (verbatim numbers) are what
`validation-report.md` records. Runtime: a few minutes, dominated by exchange rate-limit delays
across ~14 pairs × 2 paginated fetches each.

## What to check in the output

- Sample sizes per quality tier, per direction (hot/cold) — flagged as "insufficient sample" below
  ~10.
- Mean/median expected-direction return and win rate per tier, both horizons (24h, 72h).
- The permutation-test p-value for the score/outcome correlation.
- The script's own printed recommendation line.
