# 🚀 Crypto-Signal: guía rápida

Bot de alertas (solo lectura) para Binance USD-M con avisos a Telegram. Guía completa de instalación, migración a otro PC y problemas frecuentes: [`docs/DESPLIEGUE.md`](docs/DESPLIEGUE.md).

## Archivos que importan

| Archivo | Dónde | Para qué |
|---|---|---|
| `.env` | Raíz (ignorado por git) | **Secretos**: `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID` y, opcional, `GETXAPI_API_KEY`, `GEMINI_API_KEY`. Se crea copiando `.env.example`. |
| `config.yml` | Raíz (ignorado por git) | **Tu configuración**. Se crea copiando `config-clean.yml`. Se monta en solo lectura en el contenedor. |
| `config-clean.yml` | Raíz | Plantilla lista para usar (Wyckoff activo, 50 pares, RSI/MACD sin avisos). |
| `app/defaults.yml` | `app/` | Valores base del sistema. No editar. |
| `docker-compose.yml` | Raíz | Contenedor, volúmenes y límites. |

## Instalación (Docker)

```bash
git clone https://github.com/ssolis-ti/crypto-signal.git
cd crypto-signal
git checkout main

cp .env.example .env            # editar: TELEGRAM_TOKEN y TELEGRAM_CHAT_ID
cp config-clean.yml config.yml  # revisar timezone y top_n

docker compose up -d --build
docker logs -f crypto-signal    # debe mostrar "sleeping for N seconds (next cycle aligned to the clock)"
```

Credenciales de Telegram:
1. **Token:** [@BotFather](https://t.me/BotFather) → `/newbot`.
2. **Chat ID:** [@userinfobot](https://t.me/userinfobot). Escríbele antes un mensaje a tu bot para que pueda enviarte.

## Qué esperar

- El bot analiza los 50 pares de mayor volumen cada 5 minutos.
- El aviso que importa, **OPORTUNIDAD DE COMPRA**, solo puede salir justo después de que cierra una vela de 4 h (00, 04, 08, 12, 16, 20 UTC).
- Días sin avisos son normales: los avisos son raros.

## Documentación

| Documento | Contenido |
|---|---|
| [`docs/GUIA_DE_AVISOS.md`](docs/GUIA_DE_AVISOS.md) | Qué es cada aviso y qué hacer |
| [`docs/OPERACION.md`](docs/OPERACION.md) | Uso diario, revisiones, riesgos |
| [`docs/DESPLIEGUE.md`](docs/DESPLIEGUE.md) | Instalar, migrar, actualizar, tests, problemas |
| [`docs/CIERRE_PROYECTO.md`](docs/CIERRE_PROYECTO.md) | Qué funcionó, qué no, límites |
| [`docs/config.md`](docs/config.md) | Referencia completa de `config.yml` |
