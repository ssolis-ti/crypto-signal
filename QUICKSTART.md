# 🚀 Crypto-Signal: Guía Rápida

## Estructura de Archivos de Configuración

| Archivo | ¿Dónde? | ¿Para qué? |
|---------|---------|------------|
| `app/defaults.yml` | Dentro de `app/` | **NO EDITAR** - Plantilla base del sistema |
| `app/config.yml` | Dentro de `app/` | **TU CONFIGURACIÓN** - Créalo tú |
| `docker-compose.yml` | Raíz | Para Docker (no lo toques) |

## Instalación Rápida

### Opción 1: Docker (Recomendado)

```bash
git clone https://github.com/ssolis-ti/crypto-signal.git
cd crypto-signal

# Crear tu configuración
cp app/defaults.yml app/config.yml

# Editar app/config.yml con tus credenciales de Telegram

# Ejecutar
docker-compose up --build
```

### Opción 2: Python Local

```bash
git clone https://github.com/ssolis-ti/crypto-signal.git
cd crypto-signal/app

pip install -r requirements-step-1.txt
pip install -r requirements-step-2.txt

cp defaults.yml config.yml
# Editar config.yml

python app.py
```

## Configuración Mínima (`app/config.yml`)

```yaml
settings:
  update_interval: 60
  market_pairs: [BTC/USDT]
  enable_charts: true

exchanges:
  binance:
    required:
      enabled: true

notifiers:
  telegram:
    required:
      token: "TU_TOKEN"      # De @BotFather
      chat_id: "TU_CHAT_ID"  # De @userinfobot

indicators:
  rsi:
    - enabled: true
      alert_enabled: true
      signal: [rsi]
      hot: 30
      cold: 70
      candle_period: 1h
      period_count: 14
```

## Obtener Credenciales de Telegram

1. **Token**: Habla con [@BotFather](https://t.me/BotFather) → `/newbot`
2. **Chat ID**: Habla con [@userinfobot](https://t.me/userinfobot)

---

📖 Documentación completa: [`docs/config.md`](docs/config.md)
