"""
Módulo de Validación de Notificaciones
Contiene lógica para verificar que la configuración requerida esté presente.
"""

class ConfigValidator:
    """
    Clase utilitaria para validar configuraciones.
    """

    @staticmethod
    def validate_required_config(notifier, notifier_config):
        """
        Valida que los items de configuración requeridos estén presentes.

        Args:
            notifier (str): Nombre del notificador (ej. 'telegram').
            notifier_config (dict): Diccionario completo de configuración.

        Returns:
            bool: True si está configurado correctamente, False si falta algo.
        """
        notifier_configured = True
        if 'required' in notifier_config[notifier]:
            for _, val in notifier_config[notifier]['required'].items():
                if not val:
                    notifier_configured = False
        return notifier_configured
