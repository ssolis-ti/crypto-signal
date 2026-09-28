# Quickstart / Validation Guide: Notifier Core Coverage (Slice 005)

## Run just the new tests

```bash
cd app
pip install -r ../requirements-dev.txt
pytest ../tests/notifications/test_core.py -v
```

## Prove the webhook bug fix with a revert-and-retest

```bash
cd app
git stash push -- ../app/notifications/core.py
pytest ../tests/notifications/test_core.py -v -k webhook   # expected: FAILS (TypeError) pre-fix
git stash pop
pytest ../tests/notifications/test_core.py -v -k webhook   # expected: PASSES post-fix
```

## Run the full suite (regression check against slices 001-004)

```bash
cd app
pytest ../tests/ -v
```

Expected: all 58 previously-passing tests still pass, plus this slice's new tests, zero failures.
