#!/usr/bin/env python3
"""
Dashboard simple pour monitoring WikimediaAccess
"""
import json
import time
from metrics import metrics_collector
from src.generationWordpress.tools.WikimediaManager.WikimediaManagerPackage.alerts import alert_manager


def generate_dashboard_html():
    """Génère un dashboard HTML simple"""
    metrics = metrics_collector.get_metrics()

    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>WikimediaAccess Dashboard</title>
        <meta http-equiv="refresh" content="30">
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
            .container { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 20px; }
            .metric { display: inline-block; margin: 10px; padding: 15px; background: #e3f2fd; border-radius: 4px; }
            .error { background: #ffebee; color: #c62828; }
            .success { background: #e8f5e9; color: #2e7d32; }
            .warning { background: #fff3e0; color: #ef6c00; }
            table { width: 100%; border-collapse: collapse; }
            th, td { padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }
            th { background-color: #f2f2f2; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📊 WikimediaAccess Dashboard</h1>
            <p>Dernière mise à jour: {timestamp}</p>

            <div class="container">
                <h2>Métriques Globales</h2>
                <div class="metric success">
                    <strong>Appels Totaux</strong><br>
                    {total_calls}
                </div>
                <div class="metric success">
                    <strong>Succès</strong><br>
                    {total_successes}
                </div>
                <div class="metric {success_class}">
                    <strong>Taux de Succès</strong><br>
                    {global_success_rate:.1f}%
                </div>
                <div class="metric">
                    <strong>Uptime</strong><br>
                    {uptime_formatted}
                </div>
            </div>

            <div class="container">
                <h2>Détail par Opération</h2>
                <table>
                    <tr>
                        <th>Opération</th>
                        <th>Appels</th>
                        <th>Succès</th>
                        <th>Taux Succès</th>
                        <th>Temps Moyen</th>
                        <th>Erreurs</th>
                    </tr>
                    {operations_rows}
                </table>
            </div>
        </div>
    </body>
    </html>
    """

    # Formatage des données
    uptime_seconds = metrics['uptime_seconds']
    uptime_formatted = f"{int(uptime_seconds // 3600)}h {int((uptime_seconds % 3600) // 60)}m"

    global_success_rate = metrics['global']['global_success_rate']
    success_class = 'success' if global_success_rate > 95 else 'warning' if global_success_rate > 80 else 'error'

    # Génération des lignes du tableau
    operations_rows = ""
    for op_name, op_metrics in metrics['operations'].items():
        success_rate = op_metrics['success_rate_percent']
        row_class = 'success' if success_rate > 95 else 'warning' if success_rate > 80 else 'error'

        operations_rows += f"""
        <tr class="{row_class}">
            <td>{op_name}</td>
            <td>{op_metrics['total_calls']}</td>
            <td>{op_metrics['successful_calls']}</td>
            <td>{success_rate:.1f}%</td>
            <td>{op_metrics['avg_response_time_ms']:.0f}ms</td>
            <td>{op_metrics['failed_calls']}</td>
        </tr>
        """

    return html_template.format(
        timestamp=time.strftime('%Y-%m-%d %H:%M:%S'),
        total_calls=metrics['global']['total_calls'],
        total_successes=metrics['global']['total_successes'],
        global_success_rate=global_success_rate,
        success_class=success_class,
        uptime_formatted=uptime_formatted,
        operations_rows=operations_rows
    )


def main():
    """Génère et sauvegarde le dashboard"""
    html_content = generate_dashboard_html()

    with open('dashboard.html', 'w', encoding='utf-8') as f:
        f.write(html_content)

    print("📊 Dashboard généré: dashboard.html")
    print("🔗 Ouvrez dashboard.html dans votre navigateur")

    # Vérifier les alertes
    alert_manager.check_alerts()


if __name__ == "__main__":
    main()