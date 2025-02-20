import threading
import queue
import time

q = queue.Queue()

def worker():
    while not q.empty():
        task = q.get()
        print(f"Traitement de : {task}")
        time.sleep(1)  # Simulation d'une requête
        q.task_done()

# Remplir la file avec des tâches
for i in range(10):
    q.put(f"Tâche-{i}")

# Lancer des threads
threads = [threading.Thread(target=worker) for _ in range(3)]

for t in threads:
    t.start()

q.join()
