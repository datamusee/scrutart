import json
import time


def load_counter():
    try:
        with open("counter.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"count": 0, "last_reset": time.time()}


def save_counter(counter):
    with open("counter.json", "w") as f:
        json.dump(counter, f)


def make_request_with_counter():
    counter = load_counter()
    current_time = time.time()

    # Réinitialiser si une heure s'est écoulée
    if current_time - counter["last_reset"] >= 3600:
        counter = {"count": 0, "last_reset": current_time}

    if counter["count"] < 100:
        print("Requête envoyée")
        counter["count"] += 1
        save_counter(counter)
    else:
        print("Quota atteint, veuillez patienter.")


make_request_with_counter()
