# WikimediaManagerPackage/decorators.py
import functools
import time
import logging
from typing import Tuple, Any
from .exceptions import NetworkError, ValidationError


def retry_on_error(max_retries: int = 3, backoff_factor: float = 1.5,
                   retry_on_exceptions: Tuple = (NetworkError,)):
    """Décorateur pour retry avec backoff exponentiel"""

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger = logging.getLogger('WikimediaAccess')
            func_name = func.__name__

            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    if attempt > 0:
                        logger.info(f"Retry {attempt}/{max_retries} pour {func_name}")

                    result = func(*args, **kwargs)

                    if attempt > 0:
                        logger.info(f"{func_name} réussie après {attempt + 1} tentatives")

                    return result

                except retry_on_exceptions as e:
                    last_exception = e
                    if attempt == max_retries:
                        logger.error(f"{func_name} échec final après {max_retries + 1} tentatives: {str(e)}")
                        raise

                    wait_time = backoff_factor ** attempt
                    logger.warning(
                        f"{func_name} tentative {attempt + 1} échouée, retry dans {wait_time:.1f}s: {str(e)}")
                    time.sleep(wait_time)

                except ValidationError as e:
                    # Ne jamais retry les erreurs de validation
                    logger.error(f"{func_name} erreur de validation (pas de retry): {str(e)}")
                    raise

                except Exception as e:
                    logger.error(f"{func_name} erreur non-retry: {str(e)}")
                    raise

            # Ne devrait jamais arriver
            raise last_exception

        return wrapper

    return decorator