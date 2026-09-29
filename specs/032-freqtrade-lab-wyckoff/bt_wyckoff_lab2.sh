#!/usr/bin/env bash
# Ronda 2 del laboratorio Wyckoff: solo springs a 72h (senal) + simulacion realista 100 USDT.
set -u
cd "$(dirname "$0")/.."
OUTDIR="user_data/logs/wyckoff_lab"
mkdir -p "$OUTDIR"

run_one() {
    local strat="$1" per="$2" tr="$3" mode="$4" log extra wallet
    log="$OUTDIR/${strat}_${per}_${mode}.log"
    if [ "$mode" = real ]; then extra="--config user_data/config_wyckoff_real.json"; wallet=100
    else extra=""; wallet=100000; fi
    MSYS_NO_PATHCONV=1 docker compose run --rm lab backtesting \
        --config user_data/config.json --config user_data/config_wyckoff_lab.json $extra \
        --strategy "$strat" --timeframe 4h --timeframe-detail 1h --timerange "$tr" \
        --dry-run-wallet "$wallet" --breakdown year --export trades --cache none > "$log" 2>&1
    echo "$(date +%H:%M:%S) $strat $per $mode listo"
}

for job in WyckoffLab_SpringH72:signal WyckoffLab_SpringH72_SL10:signal \
           WyckoffLab_SpringH72_SL10:real WyckoffLab_SpringH72_3X_SL10:real; do
    IFS=: read -r strat mode <<< "$job"
    for p in IS:20220101-20250101 OOS:20250101-20260922; do
        IFS=: read -r per tr <<< "$p"
        while [ "$(jobs -rp | wc -l)" -ge 4 ]; do sleep 5; done
        run_one "$strat" "$per" "$tr" "$mode" &
    done
done
wait
echo listo
