# 🚀 Crypto-Signal

Bot de análisis técnico para criptomonedas con notificaciones a Telegram.

> **Versión Modernizada** - Compatible con Python 3.12+ y pandas 2.0+

---

## ✨ Características

- 📊 **+15 Indicadores técnicos**: RSI, MACD, Bollinger, Ichimoku, Stoch RSI, ADX, y más
- 📈 **Gráficos automáticos**: Genera charts con velas, RSI, MACD e Ichimoku
- 📱 **Notificaciones en tiempo real**: Telegram, Discord, Slack, Webhook
- 🔄 **Multi-exchange**: Binance, Bittrex, Coinbase Pro, y 100+ exchanges via CCXT
- ⚙️ **Altamente configurable**: Templates personalizados, umbrales ajustables

---

## 🆕 Mejoras de Esta Versión

| Mejora | Descripción |
|--------|-------------|
| **Python 3.12+** | Compatibilidad total con Python moderno |
| **Telegram v21** | Migrado a la nueva API asíncrona de python-telegram-bot |
| **Pandas 2.0+** | Corregidas deprecaciones de DataFrame.append |
| **Arquitectura modular** | Código reorganizado en paquetes (exchanges/, notifications/, rendering/) |
| **TA-Lib nativo** | Eliminada dependencia de tulipy (incompatible) |
| **Docker optimizado** | Imagen Python 3.12-slim con TA-Lib pre-compilado |

---

## 📋 Requisitos

### Para Docker (Recomendado)
- Docker Desktop instalado
- Git

### Para Instalación Local
- Python 3.12 o superior
- TA-Lib instalado en el sistema
- Git

---

## 🐳 Instalación con Docker (Recomendado)

```bash
# 1. Clonar repositorio
git clone https://github.com/ssolis-ti/crypto-signal.git
cd crypto-signal

# 2. Copiar el archivo de ejemplo a la RAÍZ del proyecto
cp app/config.yml.example config.yml

# 3. Editar config.yml (en la raíz, NO en app/)
#    Configura tu token y chat_id de Telegram
#    Usa app/config.yml.example como referencia

# 4. Ejecutar
docker compose up --build
```

> ⚠️ **IMPORTANTE**: El archivo `config.yml` debe estar en la **raíz del proyecto** (junto a `docker-compose.yml`), NO dentro de la carpeta `app/`.

---

## 💻 Instalación Local (Sin Docker)

### Requisitos previos
1. Python 3.12+ instalado
2. TA-Lib instalado:
   - **Windows**: Descargar wheel desde [aquí](https://github.com/cgohlke/talib-build/releases)
   - **Linux**: `sudo apt-get install libta-lib-dev`
   - **macOS**: `brew install ta-lib`

### Pasos

```bash
# 1. Clonar y entrar al directorio app/
git clone https://github.com/ssolis-ti/crypto-signal.git
cd crypto-signal/app

# 2. Instalar dependencias
pip install -r requirements-step-1.txt
pip install -r requirements-step-2.txt

# 3. Copiar el archivo de ejemplo
cp config.yml.example config.yml

# 4. Editar config.yml con tu token de Telegram
#    Revisa config.yml.example para ver todas las opciones

# 5. Ejecutar
python app.py
```

> 📝 **Nota**: En instalación local, el `config.yml` SÍ va dentro de `app/`.


## ⚙️ Configuración Básica

### Estructura de Archivos

| Archivo | Ubicación | Propósito |
|---------|-----------|-----------|
| `defaults.yml` | `app/` | Valores por defecto (NO EDITAR) |
| `config.yml` | `app/` | Tu configuración personal |
| `config.yml.example` | `app/` | Plantilla de ejemplo |

### Ejemplo Mínimo (`app/config.yml`)

```yaml
settings:
  update_interval: 300      # Segundos entre análisis
  market_pairs:
    - BTC/USDT
    - ETH/USDT
  enable_charts: true

exchanges:
  binance:
    required:
      enabled: true

notifiers:
  telegram:
    required:
      token: "TU_TOKEN"
      chat_id: "TU_CHAT_ID"

indicators:
  rsi:
    - enabled: true
      alert_enabled: true
      hot: 30               # RSI < 30 = Compra
      cold: 70              # RSI > 70 = Venta
      candle_period: 4h
      period_count: 14
```

---

## 📱 Configurar Telegram

1. Habla con [@BotFather](https://t.me/BotFather) y usa `/newbot`
2. Copia el **token** que te da
3. Habla con [@userinfobot](https://t.me/userinfobot) para obtener tu **chat_id**
4. Pega ambos valores en `app/config.yml`

---

## 🎨 Personalizar Notificaciones

### Variables Disponibles

| Variable | Ejemplo |
|----------|---------|
| `{{market}}` | BTC/USDT |
| `{{status}}` | hot / cold |
| `{{indicator}}` | rsi |
| `{{values}}` | {'rsi': '28.50'} |
| `{{price_value.close}}` | 95000.00 |
| `{{creation_date}}` | 2026-01-17 23:00:00 |

### Template Ejemplo

```yaml
template: |
  {% if status == 'hot' %}🟢 COMPRAR{% else %}🔴 VENDER{% endif %}
  📊 {{market}} | {{indicator|upper}}
  💵 Precio: ${{price_value.close}}
```

---

## 📊 Indicadores Disponibles

### Indicadores de Momentum
- **RSI** - Índice de Fuerza Relativa
- **Stoch RSI** - RSI Estocástico
- **MFI** - Money Flow Index
- **MACD** - Convergencia/Divergencia de Medias Móviles
- **Momentum** - Momentum clásico

### Indicadores de Tendencia
- **Ichimoku** - Nube de Ichimoku
- **ADX** - Índice Direccional Promedio
- **MA Crossover** - Cruce de Medias Móviles
- **MA Ribbon** - Cinta de Medias Móviles

### Indicadores de Volatilidad
- **Bollinger Bands** - Bandas de Bollinger
- **Squeeze Momentum** - Indicador de Compresión

### Otros
- **OBV** - On Balance Volume
- **IIV** - Incremento en Volumen (detección de pump/dump)
- **Klinger Oscillator** - Oscilador de Klinger
- **Candle Recognition** - Reconocimiento de patrones de velas

---

## 🔄 Escanear Todos los Pares

En lugar de listar cada par manualmente:

```yaml
exchanges:
  binance:
    required:
      enabled: true
    all_pairs:              # Escanea TODO contra USDT
      - USDT
    exclude:                # Excepto estos
      - USDC
      - BUSD
```

---

## 📖 Documentación Completa

Para configuraciones avanzadas, consulta [`docs/config.md`](docs/config.md).

---

## 🤝 Créditos

- Proyecto original: [CryptoSignal](https://github.com/CryptoSignal/Crypto-Signal)
- Fork mejorado: [w1ld3r/crypto-signal](https://github.com/w1ld3r/crypto-signal)
- Modernización: [ssolis-ti/crypto-signal](https://github.com/ssolis-ti/crypto-signal)

---

## 📄 Licencia

MIT License - Ver [LICENSE](LICENSE) para detalles.
