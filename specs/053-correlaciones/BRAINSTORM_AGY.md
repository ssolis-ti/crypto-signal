### 1. Veredicto honesto
**¿Se investigó?** Sí, directa e indirectamente: agrupamiento cruzado ([`specs/035`](file:///C:/Users/Proyecto%20Z/Desktop/deploy/specs/035-auditoria-resultados/AUDIT_RESULTADOS.md#L99)), lead-lag con BTC en 15m ([`specs/036`](file:///C:/Users/Proyecto%20Z/Desktop/deploy/specs/036-minutos-criticos/spec.md#L30): ruido e inversión de signo), instrumento BTC/ETH ([`specs/044`](file:///C:/Users/Proyecto%20Z/Desktop/deploy/specs/044-amplitud-capitulacion/spec.md#L64): rinden ~0%), fuerza relativa vs BTC ([`specs/049`](file:///C:/Users/Proyecto%20Z/Desktop/deploy/specs/049-debate-wyckoff/spec.md#L55): alts más castigadas rebotaron más), elasticidad intra-día ([`specs/050`](file:///C:/Users/Proyecto%20Z/Desktop/deploy/specs/050-marco-matematico/spec.md#L28): invirtió signo en OOS) y retorno residual vs BTC en 1h ([`specs/052`](file:///C:/Users/Proyecto%20Z/Desktop/deploy/specs/052-radar-intradia/spec.md#L9): azar).  
**Veredicto:** **La ventaja esperada de añadir filtros de correlación o divergencia es casi nula.**  
*Mecanismo económico:* Durante una capitulación amplia ($\ge 20\%$ pares), la cascada de liquidaciones forzadas en Binance colapsa la correlación pairwise hacia 1.0 por beta común. El ~80–85% del edge *es* justamente ese rebote beta colectivo tras barrer libros. Tratar de filtrar pares por correlación o buscar divergencias en ese instante va en contra del motor del edge. Con solo 49 días independientes ($SE = 1.05\text{ pp}$, MDE $\approx 2.9\text{ pp}$), cualquier filtro destruye la potencia.

---

### 2. Las 3 hipótesis de correlación más prometedoras

#### H1: Régimen de Correlación Previa (Rolling Average Pairwise Correlation 14d)
- **Fórmula:** $\bar{\rho}_t = \frac{2}{K(K-1)} \sum_{i < j} \text{Corr}_{14d}(r_i, r_j)$ sobre retornos 4h de los pares vigilados en los 14 días previos al evento.
- **Variable de decisión:** Solo informar en el aviso (estado de acoplamiento previo del mercado).
- **Predicción pre-registrada:** Capitulaciones amplias tras baja correlación previa ($\bar{\rho} < \text{p50}$) rebotan $\ge +0.8\text{ pp}$ más a 72h que tras regímenes sobre-acoplados (liquidación de complacencia vs pánico arrastrado).
- **Datos y fuente:** Klines 4h históricas de los 49 pares ya descargados en el repositorio (CCXT Binance USD-M).
- **Potencia estadística:** Nula/Inviable ($\sim 24$ días por celda; con MDE de 2.9 pp no hay potencia para detectar +0.8 pp; exige $\ge 120$ días).

#### H2: Dispersión Transversal de la Vela de Señal (Cross-Sectional Dispersion)
- **Fórmula:** $CSD_t = \sqrt{\frac{1}{K}\sum_{i=1}^K (r_{i,t} - \bar{r}_t)^2}$ sobre el retorno de 4h de la vela donde confirman los springs.
- **Variable de decisión:** Ajustar tamaño sugerido (reducir asignación si la dispersión es atípicamente alta).
- **Predicción pre-registrada:** Pánicos uniformes ($CSD_t < \text{p50}$ condicional a $\ge 20\%$ springs) rinden $\ge +0.8\text{ pp}$ más a 72h que eventos dispersos (donde dominan factores idiosincráticos o noticias de tokens particulares).
- **Datos y fuente:** Klines 4h locales del universo vigilado.
- **Potencia estadística:** Insuficiente ($\sim 24$ días por grupo; cualquier diferencia observada $< 2.5\text{ pp}$ será estadísticamente indistinguible de cero).

#### H3: Filtro de Shock Macro Externo (Caída Diaria en S&P 500 / DXY)
- **Fórmula:** $\Delta SPX_{24h} = (SPX_{t} - SPX_{t-24h}) / SPX_{t-24h}$ medido al cierre de la vela 4h.
- **Variable de decisión:** Solo informar (alerta de "Viento en contra macro").
- **Predicción pre-registrada:** Si $\Delta SPX_{24h} \le -1.5\%$ (o subida violenta de VIX/DXY), el rebote de la canasta se neutraliza ($\mu \le 0\%$, diferencia $\ge +1.5\text{ pp}$ vs días sin shock macro).
- **Datos y fuente:** Yahoo Finance (`yfinance`, gratuito) o FRED para `^GSPC` / `DX-Y.NYB`.
- **Potencia estadística:** Nula ($\le 10$ de los 49 días coincidirán con shocks macro severos; no cumple el piso de $\ge 30$ días por celda).

---

### 3. Idea barata que otros no propondrían
**Sincronía temporal de la liquidación en 15m (Lead-Lag de fase intra-vela):**  
En vez de correlación lineal continua, medir en qué sub-vela de 15m hicieron el mínimo y la recuperación los pares del clúster. Si $\ge 70\%$ de los pares rebotaron en las primeras 2 horas y consolidan en las últimas 2, la absorción del libro concluyó. Si los mínimos se marcaron en los últimos 30 minutos, la cascada sigue abierta al cerrar la vela 4h. Se prueba gratis con los datos 15m ya disponibles en el laboratorio.

---

### 4. Trampas metodológicas críticas
1. **Look-ahead en matrices de correlación:** Estimar correlaciones rolling o betas incluyendo la vela del crash; la volatilidad extrema contemporánea fuerza $\rho \to 1$, creando una correlación espuria sin capacidad predictiva.
2. **Sobreajuste por $N$ efectivo colapsado:** Con solo 49 días amplios, segmentar por cualquier variable de correlación deja $\le 24$ episodios por celda, garantizando falsos positivos por ruido muestral.
3. **Correlación espuria por beta común:** Las alts no tienen acoplamiento estructural entre sí; comparten el mismo motor de liquidación en Binance. Buscar cointegración o pares en pleno crash es confundir el shock de margen común con equilibrio de precios.
