# Spec 047: estructura completa de Wyckoff (acumulación y distribución)

Observación del operador: "Wyckoff, aparte del spring, tiene otras fases de acumulación y distribución y varias zonas que no has explorado".
Hasta hoy el proyecto solo validó el Spring (long) y el Upthrust (short, sin edge), más un retest suelto (spec 046). Faltaban las demás
piezas del esquema: clímax de venta, test secundario, signo de fortaleza, punto de apoyo, signo de debilidad y su contraparte de distribución.

## Universo y simulación (igual que spec 043/044; criterios fijados ANTES de correr)
Velas 4h, 49 pares del laboratorio + 177 deslistados (point-in-time), solo pares con >= 20M USD/24h en la vela de señal. Entrada a la apertura de la vela
siguiente a la señal; mantener 72 h; stop 10% contra la posición sobre mínimos/máximos; 0.1% de comisión ida y vuelta. IS 2022-24 / OOS 2025-26.
Definiciones (SMA20 de volumen; rel_vol = volumen / SMA20; ATR14 = media de 14 rangos verdaderos previos; N-máx/N-mín = máximo/mínimo de las N velas previas):

| id | evento Wyckoff | lado | regla (vela j = vela de señal) |
|---|---|---|---|
| E1 | **Clímax de venta (SC)** | long | low_j <= mín20; rel_vol >= 3.0; rango >= 1.5 x ATR14; cierre en la mitad superior de la vela |
| E2 | **Test secundario (ST) del SC** | long | tras un SC en i: primera vela r en i+3..i+15 con low dentro de +-3% del mínimo del SC, volumen <= 0.7 x volumen del SC y cierre > apertura; entrada en r+1 |
| E3 | **Signo de fortaleza (SOS)** | long | close_j > máx30; rel_vol >= 2.0; cierre en el tercio superior |
| E4 | **Punto de apoyo / backup (LPS)** | long | tras un SOS en i: primera vela r en i+1..i+5 con low <= nivel(máx30 en i) x 1.01, close >= nivel x 0.99, volumen <= SMA20 y cierre > apertura; entrada en r+1 |
| E5 | **Signo de debilidad (SOW)** | SHORT | close_j < mín30; rel_vol >= 2.0; cierre en el tercio inferior |
| E6 | **LPSY (rebote débil tras SOW)** | SHORT | tras un SOW en i: primera vela r en i+1..i+5 con high >= nivel(mín30 en i) x 0.99, close <= nivel x 1.01, volumen <= SMA20 y cierre < apertura; entrada en r+1 |
| E7 | **Spring tras caída previa (fase A)** | long | spring validado (spec 023) con retorno de las 60 velas previas (10 días) <= -20%, comparado con los springs sin esa caída previa |

Control: media incondicional del mismo lado (long o short) en cualquier vela elegible del universo (deriva de mercado).

## Criterio de aprobación (E1-E6: señales nuevas; E7: filtro)
Familia de k=7 comparaciones: IC bootstrap por DÍA al 99.3% (percentiles 0.36 / 99.64).
- E1-E6: media neta >= +1.0% en 2022-24 Y en 2025-26; exceso sobre la media incondicional > 0 con IC unido que excluye 0; >= 30 días distintos por período.
- E7: diferencia (con caída previa - sin ella) > 0 en ambos períodos, IC unido excluye 0, |dif| >= 0.5 pp, >= 30 días por celda y período.
Los shorts (E5, E6) se miden con el signo invertido; sin edge en el spec 023, así que el listón es el mismo. Si algo aprueba: NO filtra ni cambia el bot;
pasa a alerta informativa y se valida hacia adelante (>= 50 alertas). Si no: se descarta con su número.

## Resultado (resultado_wyckoff_full.txt): ninguna aprueba
Universo de 226 símbolos (49 del laboratorio + 177 deslistados), >= 20M USD/24h. Media incondicional (cualquier vela elegible): largo -0.44%, corto +0.07%.

| Evento | n | días | 2022-24 | 2025-26 | exceso vs incondicional (IC99.3% por día) |
|---|---|---|---|---|---|
| E1 clímax de venta (SC) | 1,353 | 283 | -0.15% (48%) | **+3.72%** (54%) | +0.94 [-1.40, +4.33] |
| E2 test secundario (ST) | 444 | 195 | -0.35% | -0.67% | -0.43 [-2.55, +2.84] |
| E3 signo de fortaleza (SOS) | 4,282 | 1,230 | -0.21% (40%) | -0.30% (36%) | -0.24 [-0.60, +1.04] |
| E4 backup / LPS | 1,237 | 595 | -0.34% | -0.78% | -0.44 [-0.94, +1.03] |
| E5 signo de debilidad (SOW, corto) | 3,077 | 552 | +0.38% | -0.99% | -0.09 [-1.74, +1.65] |
| E6 LPSY (corto) | 890 | 307 | -0.71% | +0.29% | -0.35 [-2.29, +1.88] |
| E7 spring tras caída previa >= 20% | 860 de 3,460 | | +1.77% vs +1.76% (dif +0.01) | +1.89% vs +1.10% (dif +0.79) | dif unida +0.25 [-4.30, +4.54] |

- **La ruptura de fortaleza (SOS) y su backup (LPS) pierden**: acierto 36-43%, medias negativas en ambos períodos (comprar rupturas con volumen en cripto 4h no funciona;
  coincide con spec 024/025). Los cortos (SOW, LPSY) tampoco: sin edge, coherente con el Upthrust.
- **El clímax de venta (SC) invierte el signo** entre períodos (-0.15% → +3.72%): ruido, no estructura. Su test secundario tampoco.
- **La "fase A" previa (caída de >= 20% antes del spring) no mejora el spring** (+0.25 pp, IC amplio). El spring del universo reproduce +1.6% (control de coherencia con spec 043).
- Lectura: de todo el esquema de Wyckoff, lo único con ventaja medible en cripto 4h es el Spring en días de capitulación amplia. Las demás fases quedan como
  "no confirmadas con reglas mecánicas": Wyckoff es un método de lectura contextual (rango, fases, causa/efecto) y una regla automática es solo una operacionalización;
  otras definiciones (rangos explícitos, otros timeframes) podrían comportarse distinto, pero cada una necesita su propio criterio pre-registrado.
