import asyncio
import aiohttp
import time
import json

# API_BASE_URL = "http://localhost:5000"
API_BASE_URL = "http://trials.grains-de-culture.fr"

async def make_request(task_id):
    """Envoie une requête à /make_request pour initier une tâche."""
    url = f"{API_BASE_URL}/make_request"
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json={"task_id": task_id}) as response:
            result = await response.json()
            print(f"Réponse du serveur: {result}")
            return result

async def check_status(task_id):
    """Fait du polling asynchrone sur /check_status/<task_id>."""
    url = f"{API_BASE_URL}/check_status/{task_id}"
    async with aiohttp.ClientSession() as session:
        while True:
            async with session.get(url) as response:
                text = await response.text()
                try:
                    status = json.loads(text)
                    print(f"Statut de la tâche {task_id}: {status['status']}")
                    if status['status'] == 'Traitement terminé':
                        print("Tâche terminée!")
                        break
                    await asyncio.sleep(2)  # Attente avant de vérifier à nouveau
                except:
                    print("erreur:", text)
async def do_other_work():
    """Exécute d'autres tâches en parallèle du polling."""
    for i in range(5):
        print(f"Faire un autre travail... {i+1}")
        await asyncio.sleep(1)

async def main():
    task_id = "12345"

    # Étape 1 : Envoyer la requête pour initier la tâche
    # await make_request(task_id)
    await make_request(task_id)

    # Étape 2 : Lancer le polling et d'autres tâches en parallèle
    await asyncio.gather(
        check_status(task_id),  # Polling de l'état de la tâche
        do_other_work()  # Autres travaux parallèles
    )

# Exécuter le test
if __name__ == "__main__":
    asyncio.run(main())
