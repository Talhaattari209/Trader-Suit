"""
Connector logging: all connectors log to logs/connector_[broker]_[date].log.
"""
import logging
from datetime import datetime
from pathlib import Path


def get_connector_logger(broker: str, logs_dir: str | Path | None = None) -> logging.Logger:
    """
    Return a logger that writes to logs/connector_{broker}_{date}.log.
    If logs_dir is None, uses project root 'logs' or current working directory.
    """
    logs_path = Path(logs_dir) if logs_dir else Path("logs")
    logs_path.mkdir(parents=True, exist_ok=True)
    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    log_file = logs_path / f"connector_{broker}_{date_str}.log"

    name = f"connector.{broker}"
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    return logger
