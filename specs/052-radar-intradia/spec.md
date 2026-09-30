# Spec 052: radar intradia (velas 1h) para movimientos por rumor

Origen: caso AVAX 2026-09-29. El radar de rumores (vela 4h cerrada, volumen >=2.5x, luego Twitter) vio el arranque con 2.45x (umbral 2.5x), y el aviso de la vela siguiente salio con el precio ya +7.5%. Brainstorm opencode + agy: el diseno espera al cierre de 4h (latencia estructural), el umbral binario es fragil, Twitter es coincidente.

## Disparador probado (regla fijada antes de ver resultados; `rumor_1h.py`)
Cierre 1h con: volumen z>=3 (mediana/MAD 30 dias, misma hora del dia), retorno residual vs BTC (beta 14d) z>=2.5, BTC sin volumen extremo (z<2.5), cooldown 12h por par. Espejo para bajista. Entrada en la apertura siguiente. 48 pares, 2022-2026.

## Resultado (retorno neto de 0.2% de comisiones)
- Long IS 2022-24: -0.28% a 1h, -0.30% a 4h, -0.35% a 24h; OOS 2025-26: -0.23%, -0.18%, -0.24%. Base (todas las horas): -0.20% a -0.29%. Es decir, igual que entrar al azar.
- Short espejo: -0.18% a +0.01% (IS), -0.27% a -0.43% (OOS): sin ventaja.
- Retorno idiosincratico (sin beta): ~0 en todos los horizontes.
- Frecuencia: ~2.4 eventos/dia con 48 pares (~1.5/dia con 30).

## Conclusion
No hay ventaja operable tras un movimiento "por rumor" detectado con volumen + retorno propio, ni long ni short. Sirve, a lo sumo, como aviso de "mira el grafico" con horas de ventaja sobre el radar de 4h. Falta el taker buy ratio (no esta en el lote historico). Como aviso: registrar primero, sin enviar.

## Auditoria de tiempos (b0f9feb)
Cada registro de `agent_state/rumor_radar.jsonl` incluye ahora `exchange_time` y `clock_skew_s` para explicar retrasos como el de 4h del radar de AVAX (causa no determinada: los logs de ese dia se perdieron).
