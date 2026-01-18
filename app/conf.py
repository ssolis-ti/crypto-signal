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

        # Merge Recursivo (Deep Merge)
        self.config = self._deep_merge(default_config, user_config)

        self.settings = self.config.get('settings', {})
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
