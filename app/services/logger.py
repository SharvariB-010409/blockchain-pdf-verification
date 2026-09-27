import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
formater = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
console_handler = logging.StreamHandler()
console_handler.setFormatter(formater)
logger.addHandler(console_handler)