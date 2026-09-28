# Quickstart / Validation Guide: Core Pipeline Test Coverage (Slice 004)

## Run just the new tests

```bash
cd app
pip install -r ../requirements-dev.txt
pytest ../tests/analyzers/test_crossover.py ../tests/data/test_pair_resolver.py \
       ../tests/notifications/test_queue.py ../tests/notifications/test_smart.py \
       ../tests/notifications/test_validator.py -v
```

## Run the full suite (regression check against slices 001-003)

```bash
cd app
pytest ../tests/ -v
```

Expected: all previously-passing 31 tests still pass, plus this slice's new tests, with zero
failures and zero skips.
