# Quickstart / Validation Guide: Read-Only Agent Integration API (Slice 009)

## Run the tests

```bash
cd app
pip install -r ../requirements-dev.txt
pytest ../tests/api/ -v
```

## Try it against the live bot

After `docker compose up -d --build` (port `127.0.0.1:8090` published per this slice):

```bash
curl -s http://127.0.0.1:8090/health
curl -s http://127.0.0.1:8090/status | python -m json.tool
curl -s http://127.0.0.1:8090/market-context | python -m json.tool
curl -s "http://127.0.0.1:8090/signals/recent?limit=10" | python -m json.tool
curl -s "http://127.0.0.1:8090/indicators?pair=BTC/USDT" | python -m json.tool
curl -s http://127.0.0.1:8090/config | python -m json.tool
```

Open `http://127.0.0.1:8090/docs` in a browser for the interactive, self-describing API explorer
(this is what lets an agent discover the schema without reading source).

## Confirm host-only exposure

```bash
docker port crypto-signal 8090   # should print 127.0.0.1:8090, not 0.0.0.0:8090
```

## Confirm no secret leakage

```bash
curl -s http://127.0.0.1:8090/config | grep -F "$(grep TELEGRAM_TOKEN ../.env | cut -d= -f2)"
# expected: no output (token not found in the response)
```
