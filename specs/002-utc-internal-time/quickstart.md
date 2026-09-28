# Quickstart / Validation Guide: UTC-Consistent Internal Time Handling

## Run the tests

```bash
cd app
pip install -r ../requirements-dev.txt
pytest ../tests/analyzers/test_utils.py ../tests/notifications/test_builder.py -v
```

## Manual cross-timezone check (User Story 1)

```bash
# Same input, two host timezones — index values must match
TZ=UTC python -c "
from analyzers.utils import IndicatorUtils
u = IndicatorUtils()
df = u.convert_to_dataframe([[1735689600000, 1, 1, 1, 1, 1]])
print(df.index[0], df.index[0].tzinfo)
"
TZ=America/Santiago python -c "
from analyzers.utils import IndicatorUtils
u = IndicatorUtils()
df = u.convert_to_dataframe([[1735689600000, 1, 1, 1, 1, 1]])
print(df.index[0], df.index[0].tzinfo)
"
```
Expected: identical printed index value and non-null `tzinfo` (UTC) in both runs.

## Regression check for `creation_date` (FR-003, SC-003)

Confirm a rendered Telegram/stdout message's `creation_date` field is unchanged before/after this
change, for the same `settings.timezone` configuration, by comparing output on a sample cycle.
