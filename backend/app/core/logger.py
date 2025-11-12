import logging
from pythonjsonlogger import jsonlogger


logger = logging.getLogger("projeto-dl")


def configure_logging():
    logger.setLevel(logging.INFO)
    logHandler = logging.StreamHandler()
    formatter = jsonlogger.JsonFormatter("%(levelname)s %(name)s %(message)s")
    logHandler.setFormatter(formatter)
    logger.addHandler(logHandler)