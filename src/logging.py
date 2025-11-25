import logging
import sys


def setup_logging(debug: bool = False) -> None:
    format_string = "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format=format_string,
        datefmt="%H:%M:%S",
        stream=sys.stdout,
    )


def get_logger(name: str) -> logging.Logger:
    """Get a named logger instance."""
    return logging.getLogger(name)
