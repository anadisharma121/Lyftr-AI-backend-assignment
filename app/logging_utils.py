import logging
from pythonjsonlogger import jsonlogger
import sys

def setup_logger(level="INFO"):
    logger = logging.getLogger("lyftr_app")
    handler = logging.StreamHandler(sys.stdout)
    
    formatter = jsonlogger.JsonFormatter(
        '%(ts)s %(level)s %(message)s %(request_id)s %(method)s %(path)s %(status)s %(latency_ms)s'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(level)
    return logger

logger = setup_logger()