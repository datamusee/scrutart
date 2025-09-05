# WikimediaManagerPackage/monitoring_decorator.py
import functools
import time
import logging
from .metrics import metrics_collector
from .exceptions import WikimediaAccessError


def monitor_operation(operation_name: str = None):
    """Décorateur pour monitorer les opérations"""

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            op_name = operation_name or func.__name__
            logger = logging.getLogger('WikimediaAccess')

            start_time = time.time()

            try:
                result = func(*args, **kwargs)

                # Enregistrer le succès
                response_time = time.time() - start_time
                metrics_collector.record_operation_success(op_name, response_time)

                logger.debug(f"Opération {op_name} réussie en {response_time:.3f}s")
                return result

            except WikimediaAccessError as e:
                # Erreur métier - enregistrer avec type
                response_time = time.time() - start_time
                error_type = type(e).__name__
                metrics_collector.record_operation_error(op_name, error_type, response_time)

                logger.error(f"Opération {op_name} échouée ({error_type}) après {response_time:.3f}s: {str(e)}")
                raise

            except Exception as e:
                # Erreur système - enregistrer comme "SystemError"
                response_time = time.time() - start_time
                metrics_collector.record_operation_error(op_name, "SystemError", response_time)

                logger.error(f"Erreur système dans {op_name} après {response_time:.3f}s: {str(e)}")
                raise

        return wrapper

    return decorator