"""Centralized logging configuration for FinReg Intelligence."""

import logging
import sys

from finreg.config.settings import get_settings


def setup_logging(log_level: str | None = None) -> logging.Logger:
    """Initialize system-wide structured logging configuration.

    Args:
        log_level: Optional log level override (e.g. 'DEBUG', 'INFO').
            Defaults to settings.log_level.
    """
    level_name = (log_level or get_settings().log_level).upper()
    level = getattr(logging, level_name, logging.INFO)

    log_format = "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s"

    logging.basicConfig(
        level=level,
        format=log_format,
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )

    logger = logging.getLogger("finreg")
    logger.setLevel(level)
    return logger
