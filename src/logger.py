"""
Logging setup for the backtesting framework.

Provides a configured logger that writes to both console and a log file.
Every order, fill, position change, and day boundary event is logged
with structured messages — far more professional than print().
"""

import os
import logging
from typing import Optional

from .config import RESULTS_DIR


_logger: Optional[logging.Logger] = None


def get_logger(
    name: str = "backtest",
    log_dir: str = RESULTS_DIR,
    log_file: str = "backtest.log",
    level: int = logging.INFO,
) -> logging.Logger:
    """
    Return the singleton framework logger.

    First call creates the logger with both console and file handlers.
    Subsequent calls return the same instance.
    """
    global _logger
    if _logger is not None:
        return _logger

    os.makedirs(log_dir, exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False

    # Formatter
    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-5s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler — INFO level
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    # File handler — DEBUG level (captures everything)
    fh = logging.FileHandler(
        os.path.join(log_dir, log_file), mode="w", encoding="utf-8"
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    _logger = logger
    return logger
