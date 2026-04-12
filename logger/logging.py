import logging
import os
import sys
from logging.handlers import RotatingFileHandler

from constants.system_config import SystemConfig

_configured = False


def _configure_root() -> None:
    global _configured
    if _configured:
        return
    _configured = True

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )
    root.addHandler(console)

    try:
        logs_dir = os.getenv("LOGS_DIR", "logs")
        os.makedirs(logs_dir, exist_ok=True)
        file_handler = RotatingFileHandler(
            os.path.join(logs_dir, "quran_api.log"),
            maxBytes=SystemConfig.MAX_BYTES.value,
            backupCount=5,
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s "
                "- [%(filename)s:%(lineno)d] - %(message)s"
            )
        )
        root.addHandler(file_handler)
    except (OSError, PermissionError):
        pass


def get_logger(name: str = "QuranAPI") -> logging.Logger:
    _configure_root()
    return logging.getLogger(name)
