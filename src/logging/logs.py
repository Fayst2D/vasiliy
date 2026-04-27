import logging
import sys
from pathlib import Path

CO_LOGGING_FORMAT = '%(levelname)s [%(asctime)s]: %(message)s'


def setup_logger(
    name: str,
    filename: str | None = None,
    stdout_level=logging.INFO,
    file_level=logging.DEBUG,
) -> logging.Logger:
    logger = logging.getLogger(name)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(stdout_level)

    formatter = logging.Formatter(CO_LOGGING_FORMAT)
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    if filename is None:
        return logger

    Path('logs').mkdir(exist_ok=True)
    file_handler = logging.FileHandler(filename, encoding='utf-8')
    file_handler.setFormatter(formatter)
    file_handler.setLevel(file_level)
    logger.addHandler(file_handler)

    logger.setLevel(logging.DEBUG)

    return logger
