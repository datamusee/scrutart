# WikimediaManagerPackage/alerts.py
import time
import logging
from typing import Dict, Any, Optional
from tools.WikimediaManager.WikimediaManagerPackage.WikimediaAccess.metrics import metrics_collector


class AlertManager:
    """Gestionnaire d'alertes simple"""

    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.alert_history = {}
        self.alert_cooldown = 300  # 5 minutes

        # Seuils d'alerte
        self.thresholds = {
            'error_rate_percent': 15.0,
            'avg_response_time_ms': 3000.0,
            'total_errors_per_hour': 50
        }

    def check_alerts(self):
        """Vérifie les métriques et déclenche les alertes si nécessaire"""
        metrics = metrics_collector.get_metrics()
        current_time = time.time()

        # Vérifier le taux d'erreur global
        global_error_rate = 100 - metrics['global']['global_success_rate']
        if global_error_rate > self.thresholds['error_rate_percent']:
            self._send_alert(
                'HIGH_ERROR_RATE',
                f"Taux d'erreur élevé: {global_error_rate:.1f}%",
                {'error_rate': global_error_rate, 'threshold': self.thresholds['error_rate_percent']},
                current_time
            )

        # Vérifier les temps de réponse par opération
        for op_name, op_metrics in metrics['operations'].items():
            if op_metrics['avg_response_time_ms'] > self.thresholds['avg_response_time_ms']:
                self._send_alert(
                    'SLOW_OPERATION',
                    f"Opération {op_name} lente: {op_metrics['avg_response_time_ms']:.1f}ms",
                    {'operation': op_name, 'response_time': op_metrics['avg_response_time_ms']},
                    current_time
                )

    def _send_alert(self, alert_type: str, message: str, context: Dict[str, Any], current_time: float):
        """Envoie une alerte avec cooldown"""
        last_alert_time = self.alert_history.get(alert_type, 0)

        if current_time - last_alert_time > self.alert_cooldown:
            self.logger.warning(f"🚨 ALERTE [{alert_type}]: {message}")
            self.logger.warning(f"Contexte: {context}")

            # Ici vous pourriez ajouter l'envoi vers Slack, email, etc.
            self.alert_history[alert_type] = current_time


# Instance globale
alert_manager = AlertManager(logging.getLogger('WikimediaAccess.Alerts'))