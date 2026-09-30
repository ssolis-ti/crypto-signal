# Despliegue en otro PC

Guía para instalar crypto-signal desde cero en otra máquina (Windows, Linux o macOS) y para mover una instalación existente conservando su historial.

## Qué es y qué necesita

crypto-signal es un bot **solo de alertas**: lee datos públicos de Binance USD-M (sin claves de exchange, no puede operar ni mover fondos) y envía avisos a Telegram. Todo corre dentro de un contenedor Docker.

Necesitas en el PC nuevo:

| Requisito | Detalle |
|---|---|
| Docker | Docker Desktop (Windows/macOS) o Docker Engine + plugin compose (Linux). |
| Git | Para clonar el repo. |
| Internet estable | Acceso a `fapi.binance.com`, `api.telegram.org` y, opcional, a GetXAPI y Gemini. |
| Un bot de Telegram | Token de [@BotFather](https://t.me/BotFather) (`/newbot`) y tu chat id ([@userinfobot](https://t.me/userinfobot)). Escríbele primero un mensaje a tu bot para que pueda escribirte. |
| Recursos | 1 CPU y ~768 MB de RAM (límite fijado en `docker-compose.yml`). Construir la imagen tarda unos minutos y descarga TA-Lib desde sourceforge. |
| Opcional | `GETXAPI_API_KEY` y `GEMINI_API_KEY` para la sección de Twitter y el radar de rumores. Sin ellas el bot funciona igual, sin esas secciones. |

## Instalación desde cero

```bash
git clone https://github.com/ssolis-ti/crypto-signal.git
cd crypto-signal
git checkout main            # o el tag v2.0 para la versión de cierre

cp .env.example .env         # Windows PowerShell: Copy-Item .env.example .env
#   editar .env: TELEGRAM_TOKEN, TELEGRAM_CHAT_ID (y opcionalmente GETXAPI_API_KEY, GEMINI_API_KEY)

cp config-clean.yml config.yml
#   revisar config.yml: timezone (por defecto America/Santiago), top_n (50 pares), etc.

docker compose up -d --build
```

Reglas de seguridad (constitución del proyecto):
- **Los secretos solo van en `.env`.** `config.yml` y `.env` están en `.gitignore`; no los subas nunca al repo.
- `config.yml` va en la raíz, junto a `docker-compose.yml`, y se monta en solo lectura.
- Cambiar `config.yml` o `.env` requiere reiniciar: `docker compose restart crypto-signal`.

## Verificar que quedó bien

```bash
docker ps                                   # crypto-signal "Up"
docker logs --since 5m crypto-signal        # busca "sleeping for N seconds (next cycle aligned to the clock)"
curl http://127.0.0.1:8090/health           # API local viva
curl http://127.0.0.1:8090/status           # pares, ciclos, último error
```

Señales de que todo está sano:
- El log muestra `wyckoff_alerts activo: un solo worker con los 50 pares`.
- Cada ciclo (5 minutos) termina con `Worker-1 sleeping for ... seconds`.
- No hay líneas `error`/`Traceback`. Un `[RELOJ] ... difiere` indica reloj del PC desfasado (el bot lo corrige con el reloj de Binance, pero conviene sincronizar el del sistema).
- Un cambio de configuración de RSI/MACD sin alertas se ve como `[SMART] No signals in cycle, skipping`: es lo esperado.

Para probar Telegram sin esperar una señal, basta con reiniciar con un indicador informativo activo (`alert_enabled: true` en `rsi`) y esperar el "Radar RSI/MACD"; luego volver a apagarlo.

## Arranque automático y suspensión del PC

- El contenedor tiene `restart: unless-stopped`: si Docker arranca, el bot arranca solo.
- **Windows/macOS:** activa "Start Docker Desktop when you sign in" y deja la sesión iniciada. Si el PC se apaga o suspende, **el bot no vigila** y no avisa que está apagado.
- Al volver, el bot revisa las 3 velas de 4 h anteriores y avisa los springs que se perdió (hasta 12 h), marcados como tardíos. Más allá de 12 h se pierden.
- Tras suspender, el reloj de Docker puede desfasarse; el bot decide qué velas cerraron usando el reloj de Binance, y cada registro guarda `clock_skew_s`.
- Para vigilancia continua real usa una máquina siempre encendida (mini PC, Raspberry con Docker, VPS). La imagen es la misma.

## Mover una instalación existente (conservar historial)

El estado vive en `app/agent_state/` (ignorado por git):
- `rumor_radar.jsonl`: registro de cada alerta y evento del radar (base de la validación hacia adelante).
- `agent_state.db`: SQLite de la API de agentes.

En el PC viejo:
```bash
docker compose down
tar czf crypto-signal-estado.tgz .env config.yml app/agent_state   # en Windows: comprimir esas rutas con 7-Zip/Explorador
```
En el PC nuevo, después de clonar el repo, extrae ese archivo en la raíz del proyecto y ejecuta `docker compose up -d --build`. Las firmas de alertas ya enviadas se reconstruyen desde `rumor_radar.jsonl` y **no se repiten avisos**. Tratar `.env` como secreto al transportarlo.

Si no copias el estado, el bot arranca limpio: puede volver a avisar los springs de las últimas 12 h y empieza un registro nuevo.

## Actualizar a una versión nueva

```bash
git pull origin main
docker compose up -d --build
```

## Ejecutar los tests

```bash
docker compose build
docker run --rm -v "$PWD:/w" -w /w deploy-crypto-signal:latest sh -c \
  "pip install -q -r requirements-dev.txt && PYTHONPATH=/w/app python -m pytest tests -q"
```
(En Git Bash de Windows antepón `MSYS_NO_PATHCONV=1`. El nombre de la imagen depende de la carpeta del proyecto: `docker images` lo muestra.) Resultado esperado: todos los tests en verde (398 al cierre).

## Problemas frecuentes

| Síntoma | Causa probable | Qué hacer |
|---|---|---|
| El contenedor sale al arrancar | Falta `config.yml` o `.env` | `docker logs crypto-signal`; crear los archivos y `docker compose up -d` |
| No llegan mensajes | Token/chat id mal, o no le escribiste a tu bot | Revisar `.env`; enviar `/start` al bot; ver `docker logs` por errores de Telegram |
| `Message is too long` o fragmentos | Texto muy largo | Poco probable: los avisos de compra pasan poco de 2.000 caracteres |
| El build falla bajando TA-Lib | sourceforge caído/bloqueado | Reintentar más tarde; el `Dockerfile` la compila desde `ta-lib-0.4.0-src.tar.gz` |
| Sin sección de Twitter | Faltan `GETXAPI_API_KEY`/`GEMINI_API_KEY` | Es normal; el aviso base sale igual |
| Avisos tardíos tras encender el PC | El bot estuvo apagado | Comportamiento esperado (ver arriba) |
| Puerto 8090 ocupado | Otro programa | Cambiar el puerto publicado en `docker-compose.yml` |

Más operación diaria en [`OPERACION.md`](OPERACION.md).
