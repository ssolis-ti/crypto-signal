# Quickstart / Validation Guide: Correct UTC Start-Date Calculation

## Run the tests

```bash
cd app
pip install -r ../requirements-dev.txt
pytest ../tests/exchanges/test_driver.py -v
```

## Manual cross-timezone check

```bash
TZ=UTC python -c "
from exchanges.driver import CCXTDriver
d = CCXTDriver.__new__(CCXTDriver)  # skip __init__ (no exchange config needed for this method)
print(d._calculate_start_date('4h', 240))
"
TZ=America/Santiago python -c "
from exchanges.driver import CCXTDriver
d = CCXTDriver.__new__(CCXTDriver)
print(d._calculate_start_date('4h', 240))
"
```
Expected: both runs print values within the same second's rounding of each other (the only variance
allowed is the sub-second gap between the two process invocations, not a multi-hour offset).
