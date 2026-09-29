# Reporte de Aseguramiento de Calidad (QA Report)

**Fecha:** 2026-09-29  
**Rol:** Ingeniero QA Senior  
**Rama de trabajo:** `qa-agy`  
**Área asignada:** QA de Datos, Exchange, Configuración y Resiliencia  

---

## 1. Resumen Ejecutivo de la Suite

- **Estado inicial:** 195 tests pasando (0 fallos).
- **Tests adversariales agregados:** 48 tests nuevos (distribuidos en 5 suites especializadas en `tests/`).
- **Estado final:** 243 tests pasando (100% verde), 0 fallos.
- **Bugs reales encontrados y solucionados:** 15 defectos en total, cubriendo fallos críticos que provocaban caída del bot (crashes), silenciamiento de ciclos completos por fallos en un solo par, o emisión de alertas falsas (false positives) basadas en datos corruptos (como volúmenes negativos o valores infinitos).

---

## 2. Bugs Reales Encontrados y Corregidos

### Área 1: Datos, Exchange y Resolución de Pares (`manager.py`, `data.py`, `driver.py`, `pair_resolver.py`)

1. **Falta de aislamiento de excepciones en `DataCollector` ante errores no contemplados**
   - **Archivo y Línea:** `app/behaviour/data.py:88-107`
   - **Entrada que lo dispara:** Cualquier excepción imprevista durante la descarga de un par (ej. `KeyError`, `TypeError`, `IndexError`, o `ccxt.NetworkError` directo lanzado por el exchange o mock).
   - **Qué pasaba:** `DataCollector._get_historical_data` solo capturaba `RetryError`, `ExchangeError`, `ValueError` y `AttributeError`. Cualquier otra excepción se propagaba y abortaba `get_all_historical_data`, cancelando la recolección para todos los demás pares del mercado.
   - **Qué debería pasar:** El error debe aislarse por par, registrarse en log y devolver lista vacía para ese par, permitiendo que el resto de los pares se recolecten con éxito.
   - **Fix aplicado:** Se agregó captura genérica `except Exception as e:` con registro estructurado y retorno seguro de lista vacía.
   - **Test que lo cubre:** `tests/data/test_qa_data_adversarial.py::TestDataCollectorAdversarial::test_pair_error_does_not_abort_other_pairs`

2. **Crash con `TypeError` en `CCXTDriver` cuando `exchange.timeframes` es `None` o inexistente**
   - **Archivo y Línea:** `app/exchanges/driver.py:96`
   - **Entrada que lo dispara:** Llamar a `get_historical_data` en un exchange de CCXT o mock donde el atributo `timeframes` es `None`.
   - **Qué pasaba:** La comprobación `if time_unit not in self.exchanges[exchange].timeframes:` lanzaba `TypeError: argument of type 'NoneType' is not iterable`.
   - **Qué debería pasar:** Validar la existencia de `timeframes` de forma segura y lanzar `ValueError` descriptivo si el timeframe no está soportado.
   - **Fix aplicado:** Se extrae `timeframes = getattr(self.exchanges[exchange], 'timeframes', None) or {}` antes de validar la pertenencia.
   - **Test que lo cubre:** `tests/data/test_qa_data_adversarial.py::TestCCXTDriverAdversarial::test_missing_timeframes_attribute_on_exchange`

3. **Inexistencia de sanitización de filas malformadas en `CCXTDriver.get_historical_data`**
   - **Archivo y Línea:** `app/exchanges/driver.py:114`
   - **Entrada que lo dispara:** Respuestas del exchange con elementos `None`, filas vacías `[]` o sin timestamp válido.
   - **Qué pasaba:** `historical_data.sort(key=lambda d: d[0])` fallaba con `TypeError` o `IndexError`.
   - **Qué debería pasar:** Descartar filas no conformes antes de ordenar y validar que queden velas válidas.
   - **Fix aplicado:** Se filtran las filas asegurando que sean listas/tuplas de longitud >= 6 con `d[0] is not None` previo al ordenamiento.
   - **Test que lo cubre:** `tests/data/test_qa_data_adversarial.py::TestCCXTDriverAdversarial::test_malformed_rows_in_ohlcv_response`

4. **Crash con `TypeError` en `PairResolver` si `dynamic_pairs.exclude` es `null`**
   - **Archivo y Línea:** `app/data/pair_resolver.py:97`
   - **Entrada que lo dispara:** Configurar en YAML `exclude: null` o dejar `exclude:` sin items.
   - **Qué pasaba:** `self.dynamic_conf.get('exclude', [])` retornaba `None` (porque la clave existía con valor nulo), y `set(None)` lanzaba `TypeError: 'NoneType' object is not iterable`, abortando el arranque.
   - **Qué debería pasar:** Tratar `None` como lista vacía y no fallar.
   - **Fix aplicado:** Se evalúa `exclude_list = self.dynamic_conf.get('exclude') or []` y se construye el conjunto de forma segura.
   - **Test que lo cubre:** `tests/data/test_qa_data_adversarial.py::TestPairResolverAdversarial::test_exclude_none_in_dynamic_config`

5. **Concatenación inválida de string e int en `PairResolver` cuando `top_n` se ingresa como cadena**
   - **Archivo y Línea:** `app/data/pair_resolver.py:105`
   - **Entrada que lo dispara:** `top_n: "10"` en la configuración YAML.
   - **Qué pasaba:** `top_n + len(exclude)` producía `TypeError: can only concatenate str (not "int") to str`.
   - **Qué debería pasar:** Coercer `top_n` a entero con fallback defensivo a 50.
   - **Fix aplicado:** Coerción segura `top_n = int(raw_top_n)` con captura de `(ValueError, TypeError)`.
   - **Test que lo cubre:** `tests/data/test_qa_data_adversarial.py::TestPairResolverAdversarial::test_top_n_as_string_in_dynamic_config`

6. **Propagación de excepciones no controladas en `PairResolver` ante caídas del exchange**
   - **Archivo y Línea:** `app/data/pair_resolver.py:102`
   - **Entrada que lo dispara:** Falla de red o exchange caído que genera `RetryError` o `NetworkError` al consultar tickers en modo dinámico.
   - **Qué pasaba:** La excepción rompía el hilo principal al resolver pares.
   - **Qué debería pasar:** Degradar de forma controlada retornando `[]` y registrando el error en los logs.
   - **Fix aplicado:** Bloque `try...except Exception:` alrededor de `get_top_pairs` retornando lista vacía.
   - **Test que lo cubre:** `tests/data/test_qa_data_adversarial.py::TestPairResolverAdversarial::test_exchange_down_dynamic_pairs_returns_empty_gracefully`

---

### Área 2: Configuración y Defaults (`conf.py`, `defaults.yml`)

7. **Destrucción de subárboles de configuración en `_deep_merge` con valores `null`**
   - **Archivo y Línea:** `app/conf.py:63-77`
   - **Entrada que lo dispara:** Usuario define secciones como `wyckoff_alerts: null`, `correlation: null` o `dynamic_pairs: null` en `config.yml`.
   - **Qué pasaba:** `_deep_merge` reemplazaba el diccionario por defecto con `None`. Posteriormente en `Behaviour.__init__`, llamadas como `config.settings.get('wyckoff_alerts', {}).get(...)` causaban `AttributeError: 'NoneType' object has no attribute 'get'`, impidiendo el inicio del bot.
   - **Qué debería pasar:** Preservar la estructura del subdiccionario por defecto cuando el override sea `None`.
   - **Fix aplicado:** En `_deep_merge`, si la clave destino es `dict` y el override es `None`, se preserva el default intacto.
   - **Test que lo cubre:** `tests/test_qa_conf_adversarial.py::TestConfAdversarial::test_null_subsections_do_not_crash_nor_overwrite_defaults_with_none`

8. **Activación accidental de heurísticos y alertas por strings truthy (`"false"`, `"0"`, `"no"`)**
   - **Archivo y Línea:** `app/conf.py:51-95`
   - **Entrada que lo dispara:** Configurar `enabled: "false"`, `"False"`, `"0"` o `"no"` en `wyckoff_alerts`, `twitter_sentiment`, `rumor_radar`, `correlation` o `enable_charts`.
   - **Qué pasaba:** En Python, cualquier string no vacío es truthy (`bool("false") is True`). El bot activaba funciones no validadas o enviaba alertas no deseadas.
   - **Qué debería pasar:** Convertir de forma estricta strings de falsedad a `False` para garantizar defaults seguros (Principio III y VII).
   - **Fix aplicado:** Se implementó `_safe_bool()` y se normalizaron todos los flags de activación (`enabled`) de `settings`.
   - **Test que lo cubre:** `tests/test_qa_conf_adversarial.py::TestConfAdversarial::test_string_false_does_not_accidentally_enable_features`

9. **`FileNotFoundError` al instanciar `Configuration` fuera del directorio `app/`**
   - **Archivo y Línea:** `app/conf.py:19-25`
   - **Entrada que lo dispara:** Instanciar `Configuration()` desde la raíz del proyecto o desde la suite de pruebas.
   - **Qué pasaba:** `open('defaults.yml')` dependía del `cwd` del proceso y fallaba si no se ejecutaba dentro de `app/`.
   - **Qué debería pasar:** Resolver la ruta de `defaults.yml` relativa al módulo `conf.py`.
   - **Fix aplicado:** Se busca `os.path.join(os.path.dirname(__file__), 'defaults.yml')` con fallback al directorio actual.
   - **Test que lo cubre:** `tests/test_qa_conf_adversarial.py::TestConfAdversarial::test_missing_config_yml_loads_defaults`

---

### Área 3: Orquestación y Estrategias (`core.py`, `strategies.py`)

10. **Falta de aislamiento de errores en bucle Wyckoff de `Behaviour.run`**
    - **Archivo y Línea:** `app/behaviour/core.py:151`
    - **Entrada que lo dispara:** Una excepción imprevista en `wyckoff_alerter.check_and_alert` para un par específico.
    - **Qué pasaba:** La excepción mataba el ciclo de análisis de `Behaviour.run`, omitiendo el análisis de los demás pares y cancelando por completo `strategy_executor.test_strategies` y `notifier.notify_all`.
    - **Qué debería pasar:** Cada par debe evaluarse de forma aislada sin que un fallo impida el procesamiento de los demás ni corte el ciclo general.
    - **Fix aplicado:** Se envolvió el llamado a `check_and_alert` en un bloque `try...except Exception:` por par dentro de `Behaviour.run`.
    - **Test que lo cubre:** `tests/behaviour/test_qa_behaviour_adversarial.py::TestBehaviourCoreAdversarial::test_exception_in_wyckoff_alerter_does_not_abort_strategy_executor_or_notifier`

11. **`StrategyExecutor._get_analysis_result` solo capturaba `TypeError`**
    - **Archivo y Línea:** `app/behaviour/strategies.py:63-73`
    - **Entrada que lo dispara:** Datos con pocas velas, ceros o NaNs que hacen que TA-Lib o los indicadores lancen `ValueError`, `IndexError` u otras excepciones.
    - **Qué pasaba:** La excepción no era capturada y abortaba el ciclo de análisis de todos los pares subsiguientes.
    - **Qué debería pasar:** Registrar warning y omitir el indicador defectuoso sin romper el procesamiento del par ni de los demás mercados.
    - **Fix aplicado:** Se amplió la captura a `except Exception as e:`, se protegió el acceso a `all_historical_data` mediante `.get()` seguro y se aisló cada par en `test_strategies`.
    - **Test que lo cubre:** `tests/behaviour/test_qa_behaviour_adversarial.py::TestBehaviourCoreAdversarial::test_strategy_executor_pair_isolation_on_indicator_error`

---

### Área 4: Workers y Persistencia de la API (`app.py`, `store.py`, `server.py`)

12. **Bucle de caída permanente a `sleep(60)` en `AnalysisWorker` si `update_interval` era string**
    - **Archivo y Línea:** `app/app.py:184`
    - **Entrada que lo dispara:** Configurar `update_interval: "300"` en settings.
    - **Qué pasaba:** `time.sleep("300")` arrojaba `TypeError: an integer or float is required`. El worker capturaba la excepción crítica y dormía 60s fijos, repitiendo el fallo en cada vuelta sin respetar jamás el intervalo deseado.
    - **Qué debería pasar:** Coercer `update_interval` a float numérico positivo válido con fallback seguro a 300.0.
    - **Fix aplicado:** Coerción numérica segura y fallback defensivo para `output_mode`.
    - **Test que lo cubre:** `tests/api/test_qa_api_adversarial.py::TestAnalysisWorkerAdversarial::test_worker_safe_sleep_with_string_interval`

13. **Vulnerabilidad a bloqueos de SQLite (`database is locked`) en `AgentStateStore`**
    - **Archivo y Línea:** `app/api/store.py:105-300`
    - **Entrada que lo dispara:** Contienda de concurrencia entre escrituras de workers y lecturas de la API de agentes.
    - **Qué pasaba:** Consultas concurrentes arrojaban `sqlite3.OperationalError: database is locked`, devolviendo errores HTTP 500 no manejados o amenazando con abortar workers.
    - **Qué debería pasar:** Configurar un timeout adecuado de espera de bloqueo (`busy_timeout`) y capturar `sqlite3.Error` en lecturas (degradando a lista vacía) y escrituras.
    - **Fix aplicado:** Se añadió `timeout=30.0` y `PRAGMA busy_timeout = 30000;` en `_connect()`, envolviendo lecturas y escrituras en captura controlada de `sqlite3.Error`.
    - **Test que lo cubre:** `tests/api/test_qa_api_adversarial.py::TestAgentStateStoreAdversarial::test_database_locked_handling`

---

### Área 5: Entrada Degenerada en Indicadores (`utils.py`, `wyckoff.py`)

14. **Colapso de `convert_to_dataframe` con listas vacías, columnas extras y timestamps string**
    - **Archivo y Línea:** `app/analyzers/utils.py:30-41`
    - **Entrada que lo dispara:** `historical_data = []`, datos con >6 columnas devueltos por exchanges, o timestamps en formato cadena `"1700000000000"`.
    - **Qué pasaba:** Asignar `dataframe.columns = [...]` con lista vacía arrojaba `ValueError: Length mismatch: Expected axis has 0 elements, new values have 6 elements`. Si venían 7 columnas arrojaba el mismo error. Al pasar timestamps como string a `to_datetime(unit='ms')` arrojaba `OutOfBoundsDatetime: Parsing to datetime overflows`.
    - **Qué debería pasar:** Devolver un DataFrame vacío con las columnas esperadas y DatetimeIndex UTC cuando la entrada esté vacía; truncar a las 6 columnas base si hay excedentes; y coercer timestamps a numérico antes de convertirlos a datetime.
    - **Fix aplicado:** Manejo especial para lista vacía, truncado `dataframe.iloc[:, :6]` y coerción numérica con `pandas.to_numeric()`.
    - **Test que lo cubre:** `tests/analyzers/test_qa_analyzers_adversarial.py::TestIndicatorUtilsAdversarial`

15. **Emisión de falsos positivos (alertas falsas) en Wyckoff con volumen negativo o valores infinitos (`inf`)**
    - **Archivo y Línea:** `app/analyzers/indicators/wyckoff.py:27-247`
    - **Entrada que lo dispara:** OHLCV con volumen negativo corrupto (ej. -500) o precios con `np.inf`/`-np.inf`.
    - **Qué pasaba:** En `relative_volume`, un volumen negativo dividido por un promedio móvil negativo generaba ratios positivos (`-1500 / -500 = +3.0`), activando el umbral de volumen extremo `>= 2.5x`. Además, en `_detect_range_event`, `-np.inf < support` y `+np.inf > resistance` evaluaban a `True`, disparando falsas señales de Spring y Upthrust sin ruptura real de mercado.
    - **Qué debería pasar:** Volúmenes `<= 0` deben ser invalidados (tratados como `NaN`), y los valores no finitos (`inf`, `-inf`) deben limpiarse e ignorarse para nunca generar señales falsas.
    - **Fix aplicado:** Sanitización en `relative_volume` descartando `volume <= 0`, reemplazo de `inf` por `nan`, y validación `np.isfinite()` en niveles de soporte, resistencia y precios de cierre en `_detect_range_event`.
    - **Test que lo cubre:** `tests/analyzers/test_qa_analyzers_adversarial.py::TestWyckoffPrimitivesAdversarial::test_negative_volume_does_not_produce_false_positive_breakouts` y `test_inf_and_nan_in_ohlcv_does_not_fire_false_events`.

---

## 3. Riesgos Detectados pero NO Modificados (y su Justificación)

1. **Sintaxis YAML corrupta en `config.yml`:**
   - *Riesgo:* Si el operador introduce un error de sintaxis grave en `config.yml` (por ejemplo caracteres de escape inválidos o indentación quebrada), `yaml.safe_load` arroja `yaml.YAMLError`.
   - *Por qué no se modificó:* Es deliberado no ocultar ni tragar un fallo de sintaxis en el archivo de configuración del usuario; si se silenciara, el bot arrancaría con defaults ignorando silenciosamente las intenciones del operador sin que este lo note.

2. **Ausencia total de pares de mercado tras filtrado:**
   - *Riesgo:* Si la resolución de pares manual y dinámica no retorna mercados activos, el bot duerme 5 minutos y finaliza su proceso.
   - *Por qué no se modificó:* Es el diseño previsto en `app/app.py:130-134` para permitir al orquestador externo o Docker reiniciar el contenedor cuando se corrijan las credenciales o conectividad.

3. **`SignalEnhancer` y scoring no predictivo:**
   - *Riesgo:* El score 0-100 sigue calculándose para los notificadores legacy y la API.
   - *Por qué no se modificó:* Conforme a la Constitución (Principio III) y las instrucciones del usuario, no se deben alterar heurísticos ni rediseñar la estrategia de trading hasta el trabajo del slice correspondiente. La alerta validada (Wyckoff 4h con volumen >= 2.5x) corre de forma completamente independiente de este score.

4. **Descarte de una sola vela en `drop_unclosed_candle`:**
   - *Riesgo:* Si un exchange devolviera múltiples velas futuras debido a un desfase de reloj extremo en el servidor remoto, la función solo poda la última vela.
   - *Por qué no se modificó:* Sigue de forma estricta la especificación `specs/001-no-repaint-signals/` ("Nunca elimina más de un elemento"), garantizando que no se reescriba ni recorte la historia de velas ya consolidadas.

---

## 4. Estado Final de la Suite y Métricas

- **Tests originales del repositorio:** 195
- **Tests adversariales agregados:** 48
  - `tests/data/test_qa_data_adversarial.py`: 21 tests
  - `tests/test_qa_conf_adversarial.py`: 6 tests
  - `tests/behaviour/test_qa_behaviour_adversarial.py`: 5 tests
  - `tests/api/test_qa_api_adversarial.py`: 8 tests
  - `tests/analyzers/test_qa_analyzers_adversarial.py`: 8 tests
- **Total tests ejecutados:** 243
- **Resultado final:** **243 passed, 5 warnings in 19.33s** (100% verde).
