import requests
import git
import os
import json
import difflib
from datetime import datetime
from requests.auth import HTTPBasicAuth
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import src.generationWordpress.configPrivee2 as configPrivee

"""
Configuration à adapter
SMTP Server : Remplacez smtp.votre_fournisseur.com par l'adresse SMTP de votre fournisseur d'email (par exemple, smtp.gmail.com pour Gmail).
Identifiants : Renseignez votre adresse email et mot de passe. Pour Gmail, utilisez un mot de passe d'application si vous avez l'authentification à deux facteurs activée.
Destinataire : Remplacez destinataire@email.com par l'adresse email de l'opérateur qui doit recevoir les alertes.
"""
"""
Etapes:
Vérifier si une page existe sur le WordPress en utilisant l'API REST.
Créer la page si elle n'existe pas.
Récupérer la version actuelle de la page depuis WordPress et la sauvegarder dans un dépôt Git.
Comparer cette version avec la précédente pour détecter des modifications externes.
Alerter l'opérateur en cas de différences.
Générer une nouvelle version de la page avec une fonction externe (non détaillée ici).
Mettre à jour la page sur WordPress et sauvegarder le code mis à jour dans le dépôt Git.
update:
Identifier la page par son ID en plus de son titre.
Comparer les différences sur le contenu brut (raw) plutôt que sur le contenu rendu (rendered).
Gérer et comparer les différences sur l'image mise en avant (featured image).

Voici une implémentation Python pour ces étapes :
"""
# Configuration
api_endpoint = f"{configPrivee.WORDPRESS_O2_API_URL}/posts?Authorization=Bearer{configPrivee.WORDPRESS_O2_PASSWORD_APP}"
# api_endpoint = f"{configPrivee.WORDPRESS_O2_API_URL}/posts?Authorization=Bearer{configPrivee.WORDPRESS_O2_PASSWORD_APP}"
api_endpoint_posts = f"{configPrivee.WORDPRESS_O2_API_URL}/posts"
bearer = f"Authorization=Bearer{configPrivee.WORDPRESS_O2_PASSWORD_APP}"
auth = (configPrivee.WORDPRESS_O2_API2USERNAME, configPrivee.WORDPRESS_O2_API2PASSWORD_APP)
username = configPrivee.WORDPRESS_O2_API2USERNAME
password = configPrivee.WORDPRESS_O2_API2PASSWORD_APP

WORDPRESS_API_URL = api_endpoint
USERNAME = configPrivee.WORDPRESS_O2_API2USERNAME
PASSWORD = configPrivee.WORDPRESS_O2_API2PASSWORD_APP
REPO_PATH = 'D:\wamp64\www\givingsense.eu\datamusee\scrutart\src\generationWordpress/trials\gitWPO2'
PAGE_TITLE = 'Test 4 process avec git'
PAGE_ID = 1194  # None Mettre un ID si nécessaire (ex : 123)

def save_page_description_to_git(page, filename):
    """Sauvegarde la description complète de la page dans le dépôt Git."""
    page_description = {
        'title': page['title']['rendered'],
        'featured_image': page.get('featured_media', None),
        'content_raw': page['content']['raw'],
        'content_rendered': page['content']['rendered'],
    }

    file_path = os.path.join(REPO_PATH, filename)
    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(page, file, ensure_ascii=False)
    repo = git.Repo(REPO_PATH)
    repo.git.add(file_path)
    repo.index.commit(f"Update {filename} on {datetime.now().isoformat()}")
    print(f"Description complète sauvegardée dans le dépôt Git : {filename}")

def load_previous_page_description(filename):
    """Charge la description complète de la page depuis le dépôt Git."""
    file_path = os.path.join(REPO_PATH, filename)
    if not os.path.exists(file_path):
        return None
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)

def compare_page_elements(previous_description, current_page):
    """Compare le contenu raw, le titre et l'image mise en avant entre deux versions."""
    differences = []

    # Comparaison du titre
    prev_title = previous_description['title']['rendered']
    curr_title = current_page['title']['rendered']
    if prev_title != curr_title:
        differences.append(f"Changement de titre : '{prev_title}' -> '{curr_title}'")

    # Comparaison du contenu brut
    prev_content_raw = previous_description['content']['raw']
    curr_content_raw = current_page['content']['raw']
    if prev_content_raw != curr_content_raw:
        differences.append("Des différences ont été détectées dans le contenu brut (raw).")

    # Comparaison de l'image mise en avant
    prev_featured_image = previous_description.get('featured_media', None)
    curr_featured_image = current_page.get('featured_media', None)
    if prev_featured_image != curr_featured_image:
        differences.append(f"Changement d'image mise en avant : '{prev_featured_image}' -> '{curr_featured_image}'")

    return differences

def extract_value(description, key):
    """Extrait la valeur associée à une clé spécifique dans la description sauvegardée."""
    for line in description.splitlines():
        if line.startswith(f"{key}:"):
            return line.split(':', 1)[1].strip()
    return None

def send_alert_email(subject, body, to_email):
    """Envoie un email d'alerte."""
    # Configuration de l'email
    from_email = "jcmoissinac@gmail.com"
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    username = "jcmoissinac@gmail.com"
    password = configPrivee.GMAILPWD

    # Création du message
    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = to_email
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain'))

    server = smtplib.SMTP(smtp_server, smtp_port)
    try:
        # Connexion au serveur SMTP et envoi de l'email
        server.starttls()
        server.login(username, password)
        server.sendmail(from_email, to_email, msg.as_string())
        print("Email d'alerte envoyé avec succès.")
    except Exception as e:
        print(f"Erreur lors de l'envoi de l'email : {e}")
    finally:
        server.quit()

def get_page(page_id=None, title=None):
    """Récupère une page par son ID ou par son titre."""
    if page_id:
        data = {
            "per_page": 1,
            "id": page_id,
            "post_type": "post",
            "context": "edit",
            "status": "publish, future, draft, pending, private"
        }
        response = requests.get(f"{WORDPRESS_API_URL}/posts/{page_id}", auth=auth, params=data)
    elif title:
        data = {
            "per_page": 1,
            "title": title,
            "post_type": "post",
            "context": "edit",
            "status": "publish, future, draft, pending, private"
        }
        response = requests.get(f"{WORDPRESS_API_URL}&search={title}", auth=auth, params=data)
    else:
        raise ValueError("Vous devez fournir soit un ID soit un titre pour récupérer la page.")

    response.raise_for_status()
    if page_id:
        page = response.json()[0]
        return page
    pages = response.json()
    for page in pages:
        if page['title']['rendered'] == title:
            return page
    return None


def save_page_to_git(page_content, filename):
    """Sauvegarde le contenu de la page dans le dépôt Git."""
    file_path = os.path.join(REPO_PATH, filename)
    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(page_content)

    repo = git.Repo(REPO_PATH)
    repo.git.add(file_path)
    repo.index.commit(f"Update {filename} on {datetime.now().isoformat()}")
    print(f"Page sauvegardée dans le dépôt Git : {filename}")


def load_previous_page(filename):
    """Charge la version précédente de la page depuis le dépôt Git."""
    file_path = os.path.join(REPO_PATH, filename)
    if not os.path.exists(file_path):
        return None
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()


def compare_versions(old_content, new_content, description="Contenu"):
    """Compare deux versions de contenu et affiche les différences."""
    diff = difflib.unified_diff(json.dumps(old_content, indent=4, ensure_ascii=False).splitlines(), json.dumps(new_content, indent=4, ensure_ascii=False).splitlines(), lineterm='', fromfile='previous', tofile='current')
    differences = '\n'.join(diff)
    if differences:
        print(f"Des différences ont été trouvées dans {description} :")
        print(differences)
        return differences
    else:
        print(f"Aucune différence détectée dans {description}.")
        return False


def create_page(title, content):
    """Crée une nouvelle page sur WordPress."""
    data = {'title': title, 'content': content, 'status': 'draft'}
    response = requests.post(WORDPRESS_API_URL, json=data, auth=auth)
    response.raise_for_status()
    return response.json()


def update_page(page_id, content):
    """Met à jour une page existante sur WordPress."""
    data = {'id': page_id, 'content': content}
    req = f"{api_endpoint_posts}/{page_id}"
    response = requests.post(req, json=data, auth=auth)
    response.raise_for_status()
    return response.json()


def get_featured_image(page):
    """Récupère l'ID de l'image mise en avant d'une page."""
    return page.get('featured_media', None)

def main():
    # Étape 1 : Récupérer la page par ID ou titre
    page = get_page(page_id=PAGE_ID, title=PAGE_TITLE)
    if not page:
        print(f"La page n'existe pas '{PAGE_TITLE}'. Création en cours...")
        new_content = "Contenu initial de la page."  # Exemple de contenu initial
        created_page = create_page(PAGE_TITLE, new_content)
        page = created_page
        save_page_description_to_git(created_page, f"{PAGE_TITLE.replace(' ', '_')}_{created_page['id']}.json")
        print(f"Page créée avec l'ID : {created_page['id']}")
        return

    # Récupérer le contenu actuel de la page
    page_id = page['id']
    filename = f"{PAGE_TITLE.replace(' ', '_')}_{page_id}.json"

    # Charger la description précédente depuis le Git
    previous_description = load_previous_page_description(filename)

    # Sauvegarder la description actuelle de la page
    save_page_description_to_git(page, filename)

    # Comparer les éléments si une version précédente existe
    if previous_description:
        differences = compare_page_elements(previous_description, page)
        if differences:
            diff_message = "\n".join(differences)
            diff_message += "\n" + compare_versions(previous_description, page)
            send_alert_email(
                subject="Alerte : Différences détectées sur la page WordPress",
                body=f"Des différences ont été détectées :\n{diff_message}",
                to_email="jcmoissinac@gmail.com"
            )
            return
        else:
            print("Aucune différence détectée.")
    else:
        print("Aucune version précédente trouvée dans le dépôt Git.")

    # Étape 2 : Générer une nouvelle version (fonction externe non spécifiée)
    new_content = "Nouveau contenu généré."  # Exemple de contenu généré

    # Mettre à jour la page sur WordPress
    updated_page = update_page(page_id, new_content)
    print(f"Page mise à jour avec succès. ID : {updated_page['id']}")

    # Sauvegarder la nouvelle description dans le dépôt Git
    save_page_description_to_git(updated_page, filename)


if __name__ == "__main__":
    main()
