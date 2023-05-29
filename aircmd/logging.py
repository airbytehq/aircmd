import logging

import structlog


# Add this function to set up logging with default settings
def setup_default_logging(log_level: str, debug_mode: bool) -> None:
    common_processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.dev.ConsoleRenderer(),
    ]

    if debug_mode:
        processors = [
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.stdlib.add_logger_name,
        ] + common_processors
    else:
        processors = common_processors

    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    logging.basicConfig(level=log_level)
    logging.getLogger("pydantic").setLevel(log_level)
