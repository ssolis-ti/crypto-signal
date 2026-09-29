#!/usr/bin/env bash
# Spec 038: experimentos pendientes, IS/OOS en modo senal.
set -u
cd "$(dirname "$0")/.."
OUTDIR="user_data/logs/exp038"; mkdir -p "$OUTDIR"
run_one() {
    local strat="$1" per="$2" tr="$3"
    MSYS_NO_PATHCONV=1 docker compose run --rm lab backtesting \
        --config user_data/config.json --config user_data/config_wyckoff_lab.json \
        --strategy "$strat" --strategy-path user_data/strategies --timeframe 4h --timeframe-detail 1h --timerange "$tr" \
        --dry-run-wallet 100000 --breakdown year --export trades --cache none > "$OUTDIR/${strat}_${per}.log" 2>&1
    echo "$(date +%H:%M:%S) $strat $per listo"
}
for strat in Exp_E0_Base Exp_E1_Sweep10 Exp_E2_Sweep15 Exp_E3_Drop24h Exp_E4_Trailing Exp_E5_TP48h Exp_E6_H48; do
    for p in IS:20220101-20250101 OOS:20250101-20260922; do
        IFS=: read -r per tr <<< "$p"
        while [ "$(jobs -rp | wc -l)" -ge 4 ]; do sleep 5; done
        run_one "$strat" "$per" "$tr" &
    done
done
wait
echo TODOS_LISTOS
