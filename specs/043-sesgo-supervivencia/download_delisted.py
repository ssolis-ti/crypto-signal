"""
Descarga velas 4h de perpetuos USDT-M DESLISTADOS desde el archivo publico de Binance (data.binance.vision).
Mensual + diario (el ultimo mes antes del deslistado solo existe como archivos diarios: justo cuando muchas
monedas se desploman, no se puede perder). Excluye acciones/ETF/materias primas tokenizadas.
"""
import io, json, re, sys, urllib.request, urllib.parse, zipfile
from concurrent.futures import ThreadPoolExecutor
import pandas as pd

BASE = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
CDN = "https://data.binance.vision"
OUT = sys.argv[1] if len(sys.argv) > 1 else "data_delisted"
START = pd.Timestamp("2021-12-01", tz="UTC")     # colchon para SMA(20) antes de 2022

NON_CRYPTO = set("""AAOI AAPL ADBE ALAB AMAT AMD AMZN ANTHROPIC APP ARM ASML ASTS AVGO AXTI BABA BE BID BITO BMNR BRKB CAT CBRS CIEN
CL COHR COIN COPPER COST CRCL CRDO CRM CRWD CRWV CSCO CSOPSAMSUNG2L CSOPSKHYNIX2L DELL DIS DJT DKNG DRAM EBAY EWJ EWT EWY EWZ FLEX
FLNC GDX GEV GLW GME GOOGL GS HANMI HD HIMS HK0700 HK1810 HOOD HPE HYUNDAI IBM INTC INTW IONQ IREN IWM JPM KLAC KODEX200 KORU KO
KUAISHOU LGELECTRONICS LITE LLY LRCX MARA MDT MEITUAN META MRK MRNA MRVL MSFT MSTR MU MUU MVLL NATGAS NAVER NBIS NET NFLX NOK NOW
NVDA NVO ONDS OPENAI ORCL PANW PAYP PDD PLTR POPMART PYPL QCOM QQQ RDDT RIVN RKLB SAMSUNGEM SAMSUNG SHOP SKHYNIX SKHY SKUU SMCI
SMH SNDK SNOW SOFI SONY SOXL SOXS SPCX SPY SQQQ STRC TBT TEM TENCENT TER TMF TQQQ TSLA TSM TTWO TXN TZA UBER UNFI URNM USAR UVXY
V VRT VST WDC WEN WMT XAG XAU XBI XLE XPD XPT ZHIPU ZM""".split())


def list_keys(prefix):
    keys, token = [], None
    while True:
        q = {"list-type": "2", "prefix": prefix, "max-keys": "1000"}
        if token:
            q["continuation-token"] = token
        xml = urllib.request.urlopen(BASE + "?" + urllib.parse.urlencode(q), timeout=60).read().decode()
        keys += re.findall(r"<Key>([^<]+\.zip)</Key>", xml)
        m = re.search(r"<NextContinuationToken>([^<]+)</NextContinuationToken>", xml)
        if not m:
            return keys
        token = m.group(1)


def fetch_zip(key):
    for _ in range(3):
        try:
            data = urllib.request.urlopen(f"{CDN}/{key}", timeout=60).read()
            z = zipfile.ZipFile(io.BytesIO(data))
            df = pd.read_csv(z.open(z.namelist()[0]), header=None)
            if not str(df.iloc[0, 0]).isdigit():
                df = df.iloc[1:]
            df = df.iloc[:, :6].astype(float)
            df.columns = ["t", "open", "high", "low", "close", "volume"]
            return df
        except Exception:
            continue
    return None


def download_symbol(sym):
    monthly = list_keys(f"data/futures/um/monthly/klines/{sym}/4h/{sym}-4h-")
    daily = list_keys(f"data/futures/um/daily/klines/{sym}/4h/{sym}-4h-")
    last_month = max((re.search(r"-(\d{4}-\d{2})\.zip", k).group(1) for k in monthly), default="0000-00")
    daily = [k for k in daily if re.search(r"-(\d{4}-\d{2})-\d{2}\.zip", k).group(1) > last_month]
    frames = [f for f in (fetch_zip(k) for k in monthly + daily) if f is not None]
    if not frames:
        return sym, None
    df = pd.concat(frames).drop_duplicates("t").sort_values("t")
    df["date"] = pd.to_datetime(df["t"], unit="ms", utc=True)
    df = df[df.date >= START].set_index("date")[["open", "high", "low", "close", "volume"]]
    return sym, df


if __name__ == "__main__":
    import os
    os.makedirs(OUT, exist_ok=True)
    syms = json.load(open("symbols.json"))["delisted"]
    syms = [s for s in syms if s[:-4] not in NON_CRYPTO]
    print("cripto deslistados a descargar:", len(syms), "(excluidos no-cripto:", len(json.load(open('symbols.json'))['delisted']) - len(syms), ")")
    done = 0
    with ThreadPoolExecutor(12) as ex:
        for sym, df in ex.map(download_symbol, syms):
            done += 1
            if df is not None and len(df) > 60:
                df.to_pickle(f"{OUT}/{sym}.pkl")
            if done % 25 == 0:
                print(f"  {done}/{len(syms)}", flush=True)
    print("guardados:", len(os.listdir(OUT)))
