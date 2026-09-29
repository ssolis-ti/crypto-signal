"""
Tests adversariales para Area 2:
- app/conf.py y defaults.yml
- Manejo de config.yml ausente, nulls, claves faltantes, deep merge
- Conversion de strings a booleano seguro (nunca activar funcion no validada por accidente)
- Variables de entorno vacias
"""
import os
from unittest.mock import patch
import pytest
import yaml

from conf import Configuration


def _load_real_defaults():
    # Ubicar defaults.yml en app/ o en la raiz
    candidates = [
        os.path.join(os.path.dirname(__file__), "..", "app", "defaults.yml"),
        os.path.join(os.path.dirname(__file__), "defaults.yml"),
        "app/defaults.yml",
        "defaults.yml",
    ]
    for p in candidates:
        if os.path.isfile(p):
            with open(p, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
    raise FileNotFoundError("defaults.yml not found in candidates")


class TestConfAdversarial:
    """Pruebas adversariales de configuracion y defaults."""

    def test_missing_config_yml_loads_defaults(self, monkeypatch):
        # Asegurar que no vea config.yml
        monkeypatch.setattr(os.path, "isfile", lambda path: False if "config.yml" in path else os.path.exists(path))
        cfg = Configuration()
        assert cfg.settings is not None
        assert cfg.settings.get("wyckoff_alerts", {}).get("enabled") is False
        assert cfg.settings.get("dynamic_pairs", {}).get("enabled") is False
        assert cfg.settings.get("correlation", {}).get("enabled") is False

    def test_null_subsections_do_not_crash_nor_overwrite_defaults_with_none(self, monkeypatch):
        """Si el usuario pone 'wyckoff_alerts: null' o 'correlation: null', no debe crashear."""
        user_yaml = """
        settings:
          wyckoff_alerts: null
          dynamic_pairs: null
          correlation: null
        notifiers: null
        """
        user_dict = yaml.safe_load(user_yaml)

        with patch("yaml.safe_load", side_effect=[
            _load_real_defaults(),
            user_dict
        ]), patch("os.path.isfile", return_value=True), patch("builtins.open"):
            cfg = Configuration()

            # wyckoff_alerts no debe ser None
            assert cfg.settings.get("wyckoff_alerts") is not None
            assert cfg.settings.get("wyckoff_alerts", {}).get("enabled") is False
            # twitter_sentiment y rumor_radar tampoco deben ser None
            wyckoff = cfg.settings.get("wyckoff_alerts", {})
            assert wyckoff.get("twitter_sentiment", {}).get("enabled") is False
            assert wyckoff.get("rumor_radar", {}).get("enabled") is False

            # correlation no debe ser None
            assert cfg.settings.get("correlation") is not None
            assert cfg.settings.get("correlation", {}).get("enabled") is False

            # notifiers no debe ser None
            assert cfg.notifiers is not None

            # to_sanitized_dict no debe crashear
            sanitized = cfg.to_sanitized_dict()
            assert isinstance(sanitized["enabled_notifiers"], list)

    def test_string_false_does_not_accidentally_enable_features(self, monkeypatch):
        """
        Si un usuario pone 'enabled: "false"' o "False" o "0" o "no",
        en Python un string no vacio es truthy!
        NUNCA debe activar una funcion no validada o de alertas por accidente.
        """
        user_yaml = """
        settings:
          enable_charts: "false"
          wyckoff_alerts:
            enabled: "false"
            twitter_sentiment:
              enabled: "false"
            rumor_radar:
              enabled: "0"
          dynamic_pairs:
            enabled: "False"
          correlation:
            enabled: "no"
        """
        user_dict = yaml.safe_load(user_yaml)

        with patch("yaml.safe_load", side_effect=[
            _load_real_defaults(),
            user_dict
        ]), patch("os.path.isfile", return_value=True), patch("builtins.open"):
            cfg = Configuration()

            assert cfg.settings.get("enable_charts") is False
            assert cfg.settings.get("wyckoff_alerts", {}).get("enabled") is False
            assert cfg.settings.get("wyckoff_alerts", {}).get("twitter_sentiment", {}).get("enabled") is False
            assert cfg.settings.get("wyckoff_alerts", {}).get("rumor_radar", {}).get("enabled") is False
            assert cfg.settings.get("dynamic_pairs", {}).get("enabled") is False
            assert cfg.settings.get("correlation", {}).get("enabled") is False

    def test_string_true_is_properly_parsed_as_bool(self, monkeypatch):
        user_yaml = """
        settings:
          wyckoff_alerts:
            enabled: "true"
        """
        user_dict = yaml.safe_load(user_yaml)

        with patch("yaml.safe_load", side_effect=[
            _load_real_defaults(),
            user_dict
        ]), patch("os.path.isfile", return_value=True), patch("builtins.open"):
            cfg = Configuration()
            assert cfg.settings.get("wyckoff_alerts", {}).get("enabled") is True

    def test_empty_env_secrets_do_not_inject_empty_tokens(self, monkeypatch):
        monkeypatch.setenv("TELEGRAM_TOKEN", "   ")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "")
        cfg = Configuration()
        telegram = cfg.notifiers.get("telegram", {})
        token = telegram.get("required", {}).get("token")
        assert token is None or token != "   "

    def test_invalid_root_type_in_user_config(self, monkeypatch):
        """Si config.yml contiene una lista o string en lugar de dict."""
        with patch("yaml.safe_load", side_effect=[
            _load_real_defaults(),
            ["invalid", "list"]
        ]), patch("os.path.isfile", return_value=True), patch("builtins.open"):
            cfg = Configuration()
            # Debe mantener defaults
            assert isinstance(cfg.settings, dict)
            assert "wyckoff_alerts" in cfg.settings
