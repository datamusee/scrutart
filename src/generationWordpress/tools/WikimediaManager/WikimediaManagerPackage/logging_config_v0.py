# WikimediaManagerPackage/logging_config.py
import logging
import logging.handlers
import os
from datetime import datetime


def setup_wikimedia_logging(log_level="INFO", log_file="logs/wikimedia_access.log"):
    """Configure le logging pour WikimediaAccess"""

    # Créer le répertoire logs si nécessaire
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    # Configuration du logger principal
    logger = logging.getLogger('WikimediaAccess')
    logger.setLevel(getattr(logging, log_level.upper()))

    # Éviter les doublons si déjà configuré
    if logger.handlers:
        return logger

    # Formateur avec contexte
    formatter = logging.Formatter(
        '%(asctime)s | %(name)s | %(levelname)s | %(funcName)s:%(lineno)d | %(message)s'
    )

    # Handler fichier avec rotation
    file_handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=10 * 1024 * 1024, backupCount=5, encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)

    # Handler console
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger