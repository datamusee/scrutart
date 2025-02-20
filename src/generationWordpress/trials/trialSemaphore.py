import threading
import time
import random

# Exemple : on limite à 2 accès simultanés
semaphore = threading.Semaphore(2)

def task(name):
    with semaphore:
        print(f"{name} accède à la ressource")
        time.sleep(random.uniform(1, 3))  # Simulation de requête à une API
        print(f"{name} a terminé")

threads = [threading.Thread(target=task, args=(f"Processus-{i}",)) for i in range(5)]

for t in threads:
    t.start()

for t in threads:
    t.join()
