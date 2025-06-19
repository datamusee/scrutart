import json

def simulate_publish_to_wordpress(title, content_html, lang, qid, target_dir):
    """Simule la création d’un article WordPress et écrit un fichier JSON."""
    post_data = {
        "title": f"{title} ({lang})",
        "slug": f"{qid.lower()}-{lang}",
        "status": "publish",
        "content": content_html,
        "lang": lang,
        "type": "post"
    }
    out_path = os.path.join(target_dir, f"post_{lang}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(post_data, f, indent=2, ensure_ascii=False)
    return f"[Simulé] Article '{title} ({lang})' sauvegardé dans {out_path}"
