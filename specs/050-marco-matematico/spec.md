# Spec 050: marco y matemática para mejorar el mejor edge (debate opencode + agy + Claude)

Origen: el operador pidió otro debate con opencode (DeepSeek) y Gemini (agy) con distintas perspectivas para mejorar el mejor edge, fijar un marco y una estructura sólidos, crear matemática
nueva aplicable y, si hace falta, investigar en arXiv, siempre orientado a mejorar el edge. Base: spring de alts líquidas en días de capitulación amplia (>= 20% de los pares elegibles con spring),
cuya ventaja es ~80-85% rebote de beta y ~15-20% estructura (spec 049). Rondas en `brainstorm/`.

## Mediciones propias para anclar el debate a datos reales (no a supuestos)
### 1. Componentes de varianza (specs/044-amplitud-capitulacion/resultado_varianza_componentes.txt)
49 días amplios, 1,478 springs (mediana 22 por día), 147 símbolos. **La sd de la media diaria de la canasta es 7.36 pp (no 4%)**; varianza dentro del día 32.9, entre días 53.0;
**ICC = 0.62**; distribución de la media diaria: p10 -9.45%, **mediana +0.57%**, p90 +12.0%; **el 45% de los días amplios tiene media negativa**. La contracción empírico-Bayes del efecto-día
es ~0.97 (sin ganancia dentro del día): toda la incertidumbre está ENTRE días. MDE real con 49 días ~2.9 pp (no 1.6).
Un CUSUM de salud del edge (k = 1.115 pp, sd 7.36) con ARL0 = 100 necesita h = 111.7 y, bajo edge muerto, tarda al menos ~100 episodios (8-10 años) en alarmar: **no sirve como alarma rápida**.
### 2. Curva de retorno acumulado por horizonte (resultado_curva_horizonte.txt; 1,476 springs, 49 días)
media diaria (IC95 por día): 4 h +0.69% [+0.25, +1.16]; 8 h +1.14%; 12 h +1.30%; 24 h **+1.35%** [+0.12, +2.64]; 32 h +0.75%; 48 h +1.02% [-0.59, +2.71]; 72 h **+1.76%** [-0.16, +3.74]; 84-96 h ~+2.1-2.15%
(máximo 92 h: +2.24%); 120 h +1.37%. El 76% de la ganancia a 72 h ya está a las 24 h y el 58% a las 48 h. Forma de DOS FASES (rebote rápido en 4-24 h, pausa en 32-48 h, segunda pierna hasta ~92 h),
no una saturación exponencial limpia; un ajuste exponencial da tau 31.5 h (media-vida 21.8 h) con RMSE 0.37, solo descriptivo.
Diferencias pareadas por día: 72 h - 24 h = +0.41 pp IC95 [-1.01, +1.81] (sd 5.10); 72 h - 48 h = +0.75 pp [-0.29, +1.82] (sd 3.86); 120 h - 72 h = -0.39 pp [-1.70, +0.87]. Correlación entre
retornos: 24 h-72 h 0.73; 48 h-72 h 0.85. **Con 49 días no se puede distinguir 24, 48 y 72 h**; el horizonte se mantiene en 72 h por el laboratorio (spec 032) y no por una media-vida medida.
Cuantiles de la media diaria a 72 h (5, 10, 25, 50, 75, 90, 95): -10.1, -9.45, -2.55, +0.57, +6.1, +12.0, +14.0 (asimetría +0.25, curtosis exceso -0.42: distribución ancha y casi plana, no de cola derecha).

## Construcción que sobrevivió al debate y se prueba: elasticidad de daño INTRA-DÍA (criterio fijado ANTES de correr)
Idea de opencode (B4) reformulada por agy: dentro de cada día se resta la media diaria (elimina la varianza entre días, tau^2 = 53) y se mide si las alts más golpeadas frente a BTC en las 48 h
previas rebotan más. Definición: D_i = -(ret 12 velas de la alt - ret 12 velas de BTC), medido en la vela de confirmación (mayor D = más golpeada); z = D estandarizado DENTRO del día; regresión
r_i - media_del_día = beta * z + e. Dirección fijada: beta > 0. Universo: springs del universo point-in-time (spec 044), en (a) días de capitulación amplia y (b) todos los días con >= 5 springs.
Aprueba SOLO si beta >= +0.5 pp por desvío estándar de D, positiva en 2022-24 Y en 2025-26, y el IC95 por día del pool excluye 0. Si aprueba: solo cambiaría la PONDERACIÓN de la canasta
(más peso a las más golpeadas) como hipótesis a validar hacia adelante; si no, se mantiene equiponderada.

### Resultado (resultado_dano_intradia.txt): NO aprueba
Días amplios (1,478 springs, 49 días): beta = +0.48 pp/sd en 2022-24 (IC95 [-0.25, +1.22]), **-0.11 pp/sd en 2025-26** [-0.54, +0.44]; unido +0.25 [-0.25, +0.80]. Velas con >= 5 springs (116 días): +0.49 [+0.02, +0.95] en 2022-24
y -0.08 en 2025-26. Signo invertido fuera de muestra. El hallazgo exploratorio de spec 049 (las más golpeadas rebotan más) no se sostiene DENTRO del día: era en buena parte un efecto entre días.
**La canasta se mantiene equiponderada.**

## MARCO FINAL CONSENSUADO (identificable con ~49 días; sd entre días 7.4 pp; ICC 0.62)
Modelo mínimo: r_{i,d} = u_d + e_{i,d}, u_d ~ (mu, tau^2), tau = 7.3 pp, e de cola gruesa; mu ≈ +1.8% a +2.2% por día amplio. Toda la incertidumbre está ENTRE días (contracción del efecto-día 0.97; el efecto par no es identificable: mediana de 6 episodios por símbolo).

| Capa | Regla congelada | Estado |
|---|---|---|
| L1 Régimen | gate BINARIO: springs / pares elegibles >= 20% (universo point-in-time, >= 20M USD/24h) | validado (lo mejor sobre lo descartado) |
| L2 Selección | canasta EQUIPONDERADA de los springs de esa vela; sin selección por par ni ponderación por daño | selección por par muerta por potencia; daño intra-día no confirmado |
| L3 Salida | 72 h con stop -10% por par | 24/48/72 h no se distinguen con 49 días (72-24: +0.41 pp [-1.0, +1.8]); curva de dos fases; se mantiene 72 h por el laboratorio |
| L4 Riesgo | distribución predictiva honesta en el aviso + tope por pérdida | fórmulas F4-F6 |
| L5 Gobierno | monitoreo secuencial (CUSUM / e-process) SOLO como gobernador pasivo (~100 episodios ≈ 10 años) + script de validación por episodio | no sirve como alarma rápida |

### Fórmulas aplicables (numpy/scipy; código de referencia en esta carpeta)
- **F1 gate:** I_d = 1{ s_d / K_d >= 0.20 }, con s_d = springs confirmados en la vela y K_d = pares elegibles (implementado: `WIDE_CLUSTER_FRACTION`).
- **F2 contracción empírico-Bayes del día:** B_d = n_d tau^2 / (n_d tau^2 + sigma^2) ≈ 0.97 (tau^2 = 53.0, sigma^2 = 32.9, n_d ≈ 22): no hay ganancia dentro del día; el efecto par colapsa a 0.
- **F3 poder honesto:** MDE = (z_{1-a/2} + z_{1-b}) sigma_Delta / sqrt(N), con sigma_Delta = sigma_dia sqrt(2(1-rho)) para pruebas pareadas y rho MEDIDA (24 h-72 h: 0.73; 48 h-72 h: 0.85). Con N = 49 y sigma = 7.36: MDE = 2.9 pp (no pareado).
- **F4 Kelly empírico (sin factores heurísticos):** g(f) = (1/D) sum_d ln(1 + f R_d), f* = argmax g; incertidumbre por remuestreo de días. Con los 49 días: f* = 3.45x (p10 0.93x, p90 5.97x); calibrado con 2022-24 (4.34x) rinde peor en 2025-26 que f = 0.25-0.5. **El óptimo teórico no es usable**; se usa un tope por pérdida.
- **F5 tope por pérdida:** f <= L / |q_p10| (q_p10 = -9.4% del día en el decil inferior): aceptar perder 1%/2%/3%/5% del capital en un día malo → f <= 0.11 / 0.21 / 0.32 / 0.53 del capital asignado a la canasta (el peor día visto, -10.1%, casi igual). Monte Carlo a 100 episodios con f = 0.30: riqueza final mediana 1.65x, p5 1.16x, P(perder) 1%, drawdown p95 19%; con f = 0.50 el drawdown p95 sube a 30%; con f = 1.0 a 52% (suponiendo que el edge persiste).
- **F6 predictiva honesta (aviso):** cuantiles de la media diaria a 72 h: p5 -10.1, p10 -9.45, p25 -2.55, p50 +0.57, p75 +6.1, p90 +12.0, p95 +14.0; 45% de días negativos; media +1.76% (IC95 por día [-0.16, +3.74]).
- **F7 CUSUM correcto:** k = (mu1 + mu0)/2, h = sigma^2/(mu1 - mu0) ln(ARL0); con sigma = 7.36: h = 111.8 y ARL1 ≈ h/k ≈ 100 episodios (~10 años). La versión de la ronda 1 (h = 0.33, ARL1 = 4.2) usaba sigma = 4% no medida.
- **F8 curva de retorno por horizonte:** 24 h +1.35%, 48 h +1.02%, 72 h +1.76%, máximo ~92 h +2.24%; dos fases (rebote rápido 4-24 h, pausa 32-48 h, segunda pierna). Descriptivo.

### Lo que murió por potencia (queda como principio de diseño, no como señal)
Índice continuo de intensidad (CIX / I_cap: 6 momentos estimados; C_sync con 6 velas y ~54 activos no es estimable); selección por par; HMM (40+ parámetros con 49 días); horizonte por modelo OU (theta = 0.038 era un número supuesto); CUSUM rápido; ponderar por daño (beta invierte signo).

### Lo que cambió en el bot por este debate
1. El aviso de capitulación amplia da la distribución POR DÍA y no una cifra por trade: mediana +0.6%, media +1.8%, 45% de los días en rojo, rango p10-p90 de -9.5% a +12%, "toma VARIOS springs" y "dimensiona pensando en perder ~10% de lo asignado en un día malo".
2. `validate_forward.py` agrega la sección por EPISODIO (referencia histórica por día, error estándar honesto, cuántos episodios hacen falta).
3. Guía de tamaño (no asume tu capital): como máximo ~0.3x del capital en la canasta si aceptas perder ~3% en un día malo; ~0.2x para ~2%.

### Literatura verificada
- Garcia Seuma (2026), arXiv:2608.03616: cascadas de liquidación subcríticas (lambda 0.1-0.2), 88% de la venta forzada en 30 min, 63% absorbida fuera de libro, salto de acoplamiento 1.6-4.4 sd. ✔ (Claude lo abrió)
- Kitron & Wengrowicz (2026), arXiv:2608.21888: reversión de corto plazo en el 90% de 183 pares de Binance, borde bruto ~1.3 pb vs 5 pb de costo. ✔ (Claude lo abrió)
- Garcia Seuma (2026), arXiv:2607.27070 ✔; Leung & Li (2014), arXiv:1411.5062 (umbrales CONSTANTES) ✔; Lipton & López de Prado (2020), arXiv:2003.10502 (con horizonte) ✔; Bacry, Mastromatteo, Muzy (2015), arXiv:1502.04592 ✔; Tibshirani et al. (2019), arXiv:1904.06019 ✔; Cheng et al. (2021), arXiv:2102.04591 ✔; Coval & Stafford (2007), JFE ✔; Brunnermeier & Pedersen (2009), RFS ✔; Liu, Tsyvinski & Wu (2022), JF ✔.
- **CITA FALSA DETECTADA:** "Baker & McHale ... arXiv:2508.18868" era una atribución errónea; ese arXiv es Lillo, Mazzarisi & Tsaknaki (2025), *Tackling estimation risk in Kelly investing using options*, que no deriva los factores usados. Baker & McHale (2013) existe en *Decision Analysis*, no en arXiv.
- Errores de la ronda 1 corregidos por los propios agentes: ARL1 del CUSUM (4.2 → ~100 episodios), theta/media-vida supuestos, factores heurísticos del Kelly bayesiano (solo (N-3)/(N-1) tiene derivación), f* de 14x (4.1x con sd real; 3.45x empírico), MDE pareados con rho supuesta.

## Límite honesto (consenso de agy y opencode)
Con 49 días se puede fijar el régimen binario, descartar el stock-picking por par y dimensionar el capital para sobrevivir a un 45% de días perdedores; alrededor de un tercio de la mejora posible es alcanzable hoy. Verificar el horizonte óptimo, un índice continuo o la degradación del edge exige entre 5 y 10 años de datos en vivo.
