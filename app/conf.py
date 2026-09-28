"""Load configuration from environment
"""

import os

import structlog
import yaml

logger = structlog.get_logger()


class Configuration():
    """Parses the environment configuration to create the config objects.
    """

    def __init__(self):
        """Initializes the Configuration class"""

        with open('defaults.yml', 'r') as config_file:
            default_config = yaml.safe_load(config_file)

        if os.path.isfile('config.yml'):
            with open('config.yml', 'r') as config_file:
                user_config = yaml.safe_load(config_file) or dict()
        else:
            user_config = dict()

        # USABILITY FIX V2: Detectar si dynamic_pairs o correlation están en la raíz
        # O accidentalmente dentro de 'exchanges' por error de indentación
        for key in ['dynamic_pairs', 'correlation']:
            # 1. Chequear en raiz
            if key in user_config:
                if 'settings' not in user_config: user_config['settings'] = {}
                if key not in user_config['settings']:
                    logger.warning(f"'{key}' found in root. Moving to 'settings'.")
                    user_config['settings'][key] = user_config[key]
            
            # 2. Chequear dentro de exchanges (error común de indentación)
            elif 'exchanges' in user_config and isinstance(user_config['exchanges'], dict):
                if key in user_config['exchanges']:
                    if 'settings' not in user_config: user_config['settings'] = {}
                    if key not in user_config['settings']:
                        logger.warning(f"'{key}' found inside 'exchanges'. Moving to 'settings'.")
                        user_config['settings'][key] = user_config['exchanges'][key]
                        # Limpiar para que no falle validación de exchanges
                        del user_config['exchanges'][key]

        # Merge Recursivo (Deep Merge)
        self.config = self._deep_merge(default_config, user_config)
        
        self.settings = self.config.get('settings', {})
        logger.debug(f"Loaded settings keys: {list(self.settings.keys())}")
        if 'dynamic_pairs' in self.settings:
            logger.debug(f"dynamic_pairs config: {self.settings['dynamic_pairs']}")
        self.notifiers = self.config.get('notifiers', {})
        self._apply_env_secrets()
        self.indicators = self.config.get('indicators', {})
        self.informants = self.config.get('informants', {})
        self.crossovers = self.config.get('crossovers', {})
        self.exchanges = self.config.get('exchanges', {})
        self.conditionals = self.config.get('conditionals', None)

    def _deep_merge(self, default, override):
        """
        Fusiona recursivamente dos diccionarios.
        Los valores de 'override' sobrescriben a 'default'.
        """
        if isinstance(default, dict) and isinstance(override, dict):
            # Copiamos default para no mutarlo
            merged = default.copy()
            for key, value in override.items():
                if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                    merged[key] = self._deep_merge(merged[key], value)
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
        telegram = self.notifiers.setdefault('telegram', {})
        required = telegram.setdefault('required', {})
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
