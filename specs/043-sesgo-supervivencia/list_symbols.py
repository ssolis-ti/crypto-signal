"""Lista los simbolos USDT-M del archivo publico de Binance (data.binance.vision) y cuales siguen activos hoy."""
import json, re, urllib.request, urllib.parse

BASE = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"


def list_prefixes(prefix):
    out, token = [], None
    while True:
        q = {"delimiter": "/", "prefix": prefix, "max-keys": "1000"}
        if token:
            q["continuation-token"] = token
            q["list-type"] = "2"
        else:
            q["list-type"] = "2"
        url = BASE + "?" + urllib.parse.urlencode(q)
        xml = urllib.request.urlopen(url, timeout=60).read().decode()
        out += re.findall(r"<Prefix>([^<]+)</Prefix>", xml)[1:] if not token else re.findall(r"<Prefix>([^<]+)</Prefix>", xml)
        m = re.search(r"<NextContinuationToken>([^<]+)</NextContinuationToken>", xml)
        if not m:
            break
        token = m.group(1)
    return out


syms = [p.rstrip("/").split("/")[-1] for p in list_prefixes("data/futures/um/monthly/klines/")]
syms = sorted(set(s for s in syms if s.endswith("USDT")))
print("simbolos USDT en el archivo:", len(syms))

info = json.load(urllib.request.urlopen("https://fapi.binance.com/fapi/v1/exchangeInfo", timeout=60))
active = {s["symbol"] for s in info["symbols"] if s["status"] == "TRADING" and s["contractType"] == "PERPETUAL"}
print("perpetuos activos hoy:", len(active))
delisted = [s for s in syms if s not in active]
print("en el archivo pero NO activos hoy (deslistados o renombrados):", len(delisted))
json.dump({"all": syms, "active": sorted(active), "delisted": delisted}, open("symbols.json", "w"))
print(delisted[:60])
