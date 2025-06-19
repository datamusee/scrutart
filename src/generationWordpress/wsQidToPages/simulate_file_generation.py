def simulate_file_generation(qid):
    task_dir = os.path.join(FILES_DIR, qid)
    os.makedirs(task_dir, exist_ok=True)
    tasks[qid] = []

    for lang in ['fr', 'en']:
        artist_name = get_artist_label(qid, lang=lang)
        paintings = get_paintings(qid, lang=lang)
        html_content = generate_html(artist_name, paintings, lang=lang)

        # Génère un fichier HTML local
        html_filename = f"{lang}.html"
        html_path = os.path.join(task_dir, html_filename)
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        tasks[qid].append(html_filename)

        # Simule publication WordPress
        result = simulate_publish_to_wordpress(artist_name, html_content, lang, qid, task_dir)
        log_file = os.path.join(task_dir, f"log_{lang}.txt")
        with open(log_file, "w", encoding="utf-8") as f:
            f.write(result)
        tasks[qid].append(f"log_{lang}.txt")
