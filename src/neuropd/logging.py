"""Structured, reproducible logging setup for NeuroPD.

Logging is configured through a single entry point so that every command-line
tool and notebook produces consistent, timestamped, level-tagged output. This
supports the reproducibility requirements in the project specification (recorded
context for every run) and the coding standard of "structured logging" rather
than bare ``print`` statements.
"""

from __future__ import annotations

import logging
import os

_DEFAULT_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DEFAULT_DATEFMT = "%Y-%m-%dT%H:%M:%S%z"


def get_logger(name: str = "neuropd") -> logging.Logger:
    """Return a namespaced logger.

    Parameters
    ----------
    name:
        Logger name. Sub-loggers should use dotted names such as
        ``"neuropd.preprocessing"`` so that per-module verbosity can be tuned.
    """
    return logging.getLogger(name)


def configure_logging(level: int | str | None = None) -> logging.Logger:
    """Configure the root ``neuropd`` logger idempotently.

    Parameters
    ----------
    level:
        Logging level as an ``int`` or name (e.g. ``"INFO"``). If ``None``, the
        ``NEUROPD_LOG_LEVEL`` environment variable is consulted, defaulting to
        ``"INFO"``.

    Returns
    -------
    logging.Logger
        The configured ``neuropd`` logger.

    Notes
    -----
    This function does not touch the global root logger configuration of the host
    application; it only attaches a single stream handler to the ``neuropd``
    logger and prevents duplicate handlers on repeated calls.
    """
    if level is None:
        level = os.environ.get("NEUROPD_LOG_LEVEL", "INFO")
    if isinstance(level, str):
        level = logging.getLevelName(level.upper())

    logger = logging.getLogger("neuropd")
    logger.setLevel(level)

    if not any(getattr(h, "_neuropd_handler", False) for h in logger.handlers):
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(_DEFAULT_FORMAT, datefmt=_DEFAULT_DATEFMT))
        handler._neuropd_handler = True  # type: ignore[attr-defined]
        logger.addHandler(handler)

    logger.propagate = False
    return logger
