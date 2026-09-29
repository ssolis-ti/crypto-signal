#!/usr/bin/env bash
# Bateria de backtests del laboratorio Wyckoff (crypto-signal specs/032).
#   bash ops/bt_wyckoff_lab.sh
# Logs en user_data/logs/wyckoff_lab/<estrategia>_<periodo>.log
set -u
cd "$(dirname "$0")/.."
OUTDIR="user_data/logs/wyckoff_lab"
MAXJ="${MAXJ:-4}"
mkdir -p "$OUTDIR"

run_one() {
    local strat="$1" per="$2" tr="$3" log="$OUTDIR/${strat}_${per}.log" intento
    for intento in 1 2 3; do
        MSYS_NO_PATHCONV=1 docker compose run --rm lab backtesting \
            --config user_data/config.json --config user_data/config_wyckoff_lab.json \
            --strategy "$strat" --timeframe 4h --timeframe-detail 1h --timerange "$tr" \
            --dry-run-wallet 100000 --breakdown year --export trades --cache none \
            > "$log" 2>&1
        grep -qE "Could not read schema|Unable to use Arrow|ArrowInvalid" "$log" || break
        sleep $((intento * 7))
    done
    echo "$(date +%H:%M:%S) $strat $per listo"
}

start=$(date +%s)
for strat in WyckoffLab_H1 WyckoffLab_H2 WyckoffLab_H24 WyckoffLab_H72 WyckoffLab_H7D \
             WyckoffLab_H14D WyckoffLab_H7D_SL10 WyckoffLab_H7D_3X_SL10; do
    for job in IS:20220101-20250101 OOS:20250101-20260922; do
        IFS=: read -r per tr <<< "$job"
        while [ "$(jobs -rp | wc -l)" -ge "$MAXJ" ]; do sleep 5; done
        run_one "$strat" "$per" "$tr" &
    done
done
wait
echo "listo: 16 backtests en $(( ($(date +%s) - start) / 60 )) min"
