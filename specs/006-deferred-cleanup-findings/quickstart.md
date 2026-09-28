# Quickstart / Validation Guide: Deferred Cleanup Findings (Slice 006)

## Run just the new/extended tests

```bash
cd app
pip install -r ../requirements-dev.txt
pytest ../tests/data/test_manager.py -v -k TopPairs
pytest ../tests/rendering/test_utils.py -v
pytest ../tests/utils/test_calibration.py -v
```

## Confirm no leftover DEBUG-prefixed logging

```bash
grep -n "DEBUG:" app/data/manager.py   # expected: no output
```

## Run the full suite (regression check against slices 001-005)

```bash
cd app
pytest ../tests/ -v
```

Expected: all 77 previously-passing tests still pass, plus this slice's new tests, zero failures.
