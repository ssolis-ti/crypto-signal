"""Configure application logger
"""

import logging
import sys

import structlog


def configure_logging(loglevel, log_mode):
    """Configure the application logger

    Args:
        loglevel (str): The level of logging for the application.
        log_mode (str): What kind of logging output to apply...
            text: Text logging is intended for users / developers.
            json: Json logging is intended for parsing with a log aggregation system.
    """

    if not loglevel:
        loglevel = logging.INFO

    if log_mode == 'json':
        # Fallback to standard logging for JSON mode as python-json-logger was removed
        log_formatter = logging.Formatter('%(message)s')
    elif log_mode == 'text':
        log_formatter = logging.Formatter('%(message)s')
    elif log_mode == 'standard':
        log_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    else:
        log_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(log_formatter)
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(loglevel)
    
    # Silenciar loggers ruidosos de librerías externas
    noisy_loggers = [
        'urllib3', 'requests', 'ccxt', 'httpcore', 'httpx',
        'urllib3.connectionpool', 'urllib3.util.retry',
        'telegram', 'telegram.ext', 'httpcore.http11',
        'asyncio', 'matplotlib', 'PIL'
    ]
    for logger_name in noisy_loggers:
        logging.getLogger(logger_name).setLevel(logging.WARNING)

    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.stdlib.render_to_log_kwargs,
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True
    )
