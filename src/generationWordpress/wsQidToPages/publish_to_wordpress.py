import base64

def publish_to_wordpress(title, content_html, lang, qid, wp_config):
    """Publie une page sur WordPress et retourne l’ID et l’URL."""
    user = wp_config["user"]
    password = wp_config["password"]
    base_url = wp_config["api_url"].rstrip('/')

    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    headers = {
        "Authorization": f"Basic {token}",
        "Content-Type": "application/json"
    }

    data = {
        "title": f"{title} ({lang})",
        "content": content_html,
        "status": "publish",
        "slug": f"{qid.lower()}-{lang}",
        "lang": lang  # si Polylang ou WPML est installé
    }

    response = requests.post(f"{base_url}/wp/v2/pages", json=data, headers=headers)
    if not response.ok:
        raise RuntimeError(f"Erreur WP ({lang}): {response.text}")
    return response.json()["id"], response.json()["link"]
