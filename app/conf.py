"""Load configuration from environment
"""

import os

import structlog
import yaml

logger = structlog.get_logger()


def _safe_bool(value, default: bool = False) -> bool:
    """Convierte de forma determinista y segura a booleano, protegiendo contra strings truthy."""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        clean = value.strip().lower()
        if clean in ('true', '1', 'yes', 'on', 't'):
            return True
        if clean in ('false', '0', 'no', 'off', 'f', 'none', 'null', ''):
            return False
    return default


class Configuration():
    """Parses the environment configuration to create the config objects.
    """

    def __init__(self):
        """Initializes the Configuration class"""

        defaults_path = os.path.join(os.path.dirname(__file__), 'defaults.yml')
        if not os.path.isfile(defaults_path):
            defaults_path = 'defaults.yml'

        with open(defaults_path, 'r') as config_file:
            default_config = yaml.safe_load(config_file) or dict()

        config_path = 'config.yml'
        if not os.path.isfile(config_path):
            alt_path = os.path.join(os.path.dirname(__file__), '..', 'config.yml')
            if os.path.isfile(alt_path):
                config_path = alt_path

        if os.path.isfile(config_path):
            with open(config_path, 'r') as config_file:
                raw_user = yaml.safe_load(config_file)
                user_config = raw_user if isinstance(raw_user, dict) else dict()
        else:
            user_config = dict()

        # USABILITY FIX V2: Detectar si dynamic_pairs o correlation están en la raíz
        # O accidentalmente dentro de 'exchanges' por error de indentación
        for key in ['dynamic_pairs', 'correlation']:
            # 1. Chequear en raiz
            if key in user_config:
                if 'settings' not in user_config or not isinstance(user_config['settings'], dict):
                    user_config['settings'] = {}
                if key not in user_config['settings']:
                    logger.warning(f"'{key}' found in root. Moving to 'settings'.")
                    user_config['settings'][key] = user_config[key]
            
            # 2. Chequear dentro de exchanges (error común de indentación)
            elif 'exchanges' in user_config and isinstance(user_config['exchanges'], dict):
                if key in user_config['exchanges']:
                    if 'settings' not in user_config or not isinstance(user_config['settings'], dict):
                        user_config['settings'] = {}
                    if key not in user_config['settings']:
                        logger.warning(f"'{key}' found inside 'exchanges'. Moving to 'settings'.")
                        user_config['settings'][key] = user_config['exchanges'][key]
                        # Limpiar para que no falle validación de exchanges
                        del user_config['exchanges'][key]

        # Merge Recursivo (Deep Merge)
        self.config = self._deep_merge(default_config, user_config)
        
        self.settings = self.config.get('settings') if isinstance(self.config.get('settings'), dict) else {}
        logger.debug(f"Loaded settings keys: {list(self.settings.keys())}")
        if 'dynamic_pairs' in self.settings:
            logger.debug(f"dynamic_pairs config: {self.settings['dynamic_pairs']}")

        # Normalización segura de tipos booleanos (defaults seguros)
        self.settings['enable_charts'] = _safe_bool(self.settings.get('enable_charts', False))

        # wyckoff_alerts: garantizar sub-dicts y flags booleanos
        wyckoff = self.settings.get('wyckoff_alerts')
        if not isinstance(wyckoff, dict):
            wyckoff = {}
            self.settings['wyckoff_alerts'] = wyckoff
        wyckoff['enabled'] = _safe_bool(wyckoff.get('enabled', False))

        ts = wyckoff.get('twitter_sentiment')
        if not isinstance(ts, dict):
            ts = {}
            wyckoff['twitter_sentiment'] = ts
        ts['enabled'] = _safe_bool(ts.get('enabled', False))

        rr = wyckoff.get('rumor_radar')
        if not isinstance(rr, dict):
            rr = {}
            wyckoff['rumor_radar'] = rr
        rr['enabled'] = _safe_bool(rr.get('enabled', False))

        # dynamic_pairs
        dynamic = self.settings.get('dynamic_pairs')
        if not isinstance(dynamic, dict):
            dynamic = {}
            self.settings['dynamic_pairs'] = dynamic
        dynamic['enabled'] = _safe_bool(dynamic.get('enabled', False))

        # correlation
        corr = self.settings.get('correlation')
        if not isinstance(corr, dict):
            corr = {}
            self.settings['correlation'] = corr
        corr['enabled'] = _safe_bool(corr.get('enabled', False))
        qf = corr.get('quality_filter')
        if not isinstance(qf, dict):
            qf = {}
            corr['quality_filter'] = qf
        qf['enabled'] = _safe_bool(qf.get('enabled', False))

        self.notifiers = self.config.get('notifiers') if isinstance(self.config.get('notifiers'), dict) else {}
        self._apply_env_secrets()
        self.indicators = self.config.get('indicators') if isinstance(self.config.get('indicators'), dict) else {}
        self.informants = self.config.get('informants') if isinstance(self.config.get('informants'), dict) else {}
        self.crossovers = self.config.get('crossovers') if isinstance(self.config.get('crossovers'), dict) else {}
        self.exchanges = self.config.get('exchanges') if isinstance(self.config.get('exchanges'), dict) else {}
        self.conditionals = self.config.get('conditionals', None)

    def _deep_merge(self, default, override):
        """
        Fusiona recursivamente dos diccionarios.
        Los valores de 'override' sobrescriben a 'default'.
        Si un valor en override es None para una seccion que en default es dict,
        se preserva el default para mantener la estructura intacta.
        """
        if not isinstance(override, dict):
            return default.copy() if isinstance(default, dict) else default

        if isinstance(default, dict):
            merged = default.copy()
            for key, value in override.items():
                if key in merged and isinstance(merged[key], dict):
                    if isinstance(value, dict):
                        merged[key] = self._deep_merge(merged[key], value)
                    elif value is None:
                        # Preservar el default de la subseccion
                        continue
                    else:
                        merged[key] = value
                else:
                    merged[key] = value
            return merged
        return override

    def _apply_env_secrets(self):
        """
        Credenciales desde variables de entorno (archivo .env vía docker compose), para no
        guardarlas en config.yml. Si TELEGRAM_TOKEN / TELEGRAM_CHAT_ID existen, tienen prioridad.
        """
        token = os.environ.get('TELEGRAM_TOKEN', '').strip()
        chat_id = os.environ.get('TELEGRAM_CHAT_ID', '').strip()
        if not (token or chat_id):
            return
        if not isinstance(self.notifiers, dict):
            self.notifiers = {}
        telegram = self.notifiers.setdefault('telegram', {})
        if not isinstance(telegram, dict):
            telegram = {}
            self.notifiers['telegram'] = telegram
        required = telegram.setdefault('required', {})
        if not isinstance(required, dict):
            required = {}
            telegram['required'] = required
        if token:
            required['token'] = token
        if chat_id:
            required['chat_id'] = chat_id

    def to_sanitized_dict(self) -> dict:
        """
        Config apta para exponer via API (app/api/server.py::/config, specs/009-agent-api/).

        Allow-list explicito, no deny-list: copia settings/indicators/informants/crossovers
        tal cual (no contienen secretos), y de notifiers/exchanges solo expone que claves
        estan configuradas/habilitadas -- nunca el contenido de ningun bloque 'required'
        (token, chat_id, url, credenciales), sin importar como se llame el campo dentro de
        el. Ver specs/009-agent-api/research.md.
        """
        enabled_exchanges = [
            name for name, cfg in self.exchanges.items()
            if isinstance(cfg, dict) and cfg.get('required', {}).get('enabled', False)
        ]
        return {
            'settings': self.settings,
            'indicators': self.indicators,
            'informants': self.informants,
            'crossovers': self.crossovers,
            'enabled_notifiers': list(self.notifiers.keys()),
            'enabled_exchanges': enabled_exchanges,
        }
