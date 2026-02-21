import logging


class Logger:
    _initialized: bool = False

    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        logger = logging.getLogger(name)
        if not cls._initialized:
            cls._init_root()
            cls._initialized = True
        return logger

    @classmethod
    def _init_root(cls) -> None:
        root = logging.getLogger()
        if not root.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(
                logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            )
            root.addHandler(handler)
            root.setLevel(logging.INFO)
