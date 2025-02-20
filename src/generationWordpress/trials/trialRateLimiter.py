import time
from ratelimit import limits, sleep_and_retry

# Limite de 100 requêtes par heure (3600 secondes)
ONE_HOUR = 3600

@sleep_and_retry
@limits(calls=100, period=ONE_HOUR)
def make_request():
    print("Requête envoyée")
    # Simulation de requête à une API
    time.sleep(0.1)

# Exemple de boucle de requêtes
for _ in range(105):
    try:
        make_request()
    except Exception as e:
        print("Limite atteinte", e)
