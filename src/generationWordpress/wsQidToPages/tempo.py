import threading
import time
import json
import traceback

# --- Tâches ---

def task_1(input_data):
    time.sleep(1)
    return {"value": 10, "status": "done"}

def task_2(input_data):
    time.sleep(1)
    if input_data["value"] == 10:
        raise ValueError("Erreur dans task_2 (valeur interdite)")
    return {"value": input_data["value"] * 3, "status": "done"}

def task_3(input_data):
    time.sleep(1)
    return {"value": input_data["value"] + 5, "status": "done"}

# --- Transitions ---

def transition_1_to_2(result_1):
    return {"value": result_1["value"]}

def transition_2_to_3(result_2):
    return {"value": result_2["value"]}

# --- Runner séquentiel dans un seul thread ---

class TaskChainRunner(threading.Thread):
    def __init__(self, tasks, transitions, initial_input):
        super().__init__()
        self.tasks = tasks
        self.transitions = transitions
        self.initial_input = initial_input
        self.results = {}
        self.success = True
        self.error = None

    def run(self):
        input_data = self.initial_input
        for i, task in enumerate(self.tasks):
            task_name = f"task_{i+1}"
            try:
                print(f"→ Démarrage {task_name}")
                result = task(input_data)
                self.results[task_name] = result
                print(f"✓ {task_name} terminé : {result}")
                if i < len(self.transitions):
                    input_data = self.transitions[i](result)
            except Exception as e:
                self.success = False
                self.error = {
                    "task": task_name,
                    "message": str(e),
                    "traceback": traceback.format_exc()
                }
                print(f"✗ Erreur dans {task_name} : {e}")
                break

# --- Configuration ---

tasks = [task_1, task_2, task_3]
transitions = [transition_1_to_2, transition_2_to_3]
initial_input = {}

# --- Exécution dans un seul thread ---

runner = TaskChainRunner(tasks, transitions, initial_input)
runner.start()
runner.join()

# --- Affichage des résultats ---

if runner.success:
    print("\n✅ Toutes les tâches ont réussi.")
else:
    print("\n❌ Une erreur est survenue.")
    print(json.dumps(runner.error, indent=2))

print("\n📦 Résultats complets :")
print(json.dumps(runner.results, indent=2))
