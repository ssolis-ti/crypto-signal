"""Load configuration from environment
"""

import os

import ccxt
import yaml


class Configuration():
    """Parses the environment configuration to create the config objects.
    """

    def __init__(self):
        """Initializes the Configuration class"""

        with open('defaults.yml', 'r') as config_file:
            default_config = yaml.load(config_file, Loader=yaml.FullLoader)

        if os.path.isfile('config.yml'):
            with open('config.yml', 'r') as config_file:
                user_config = yaml.load(config_file, Loader=yaml.FullLoader)
        else:
            user_config = dict()

        # USABILITY FIX V2: Detectar si dynamic_pairs o correlation están en la raíz
        # O accidentalmente dentro de 'exchanges' por error de indentación
        for key in ['dynamic_pairs', 'correlation']:
            # 1. Chequear en raiz
            if key in user_config:
                if 'settings' not in user_config: user_config['settings'] = {}
                if key not in user_config['settings']:
                    print(f"WARNING: '{key}' found in root. Moving to 'settings'.")
                    user_config['settings'][key] = user_config[key]
            
            # 2. Chequear dentro de exchanges (error común de indentación)
            elif 'exchanges' in user_config and isinstance(user_config['exchanges'], dict):
                if key in user_config['exchanges']:
                    if 'settings' not in user_config: user_config['settings'] = {}
                    if key not in user_config['settings']:
                        print(f"WARNING: '{key}' found inside 'exchanges'. Moving to 'settings'.")
                        user_config['settings'][key] = user_config['exchanges'][key]
                        # Limpiar para que no falle validación de exchanges
                        del user_config['exchanges'][key]

        # Merge Recursivo (Deep Merge)
        self.config = self._deep_merge(default_config, user_config)
        
        self.settings = self.config.get('settings', {})
        print(f"DEBUG: Loaded settings keys: {list(self.settings.keys())}")
        if 'dynamic_pairs' in self.settings:
            print(f"DEBUG: dynamic_pairs config: {self.settings['dynamic_pairs']}")
        self.notifiers = self.config.get('notifiers', {})
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

        for exchange in ccxt.exchanges:
            if exchange not in self.exchanges:
                self.exchanges[exchange] = {
                    'required': {
                        'enabled': False
                    }
                }
