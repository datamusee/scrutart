from flask import Flask, render_template, request, jsonify
import json, os

app = Flask(__name__)
JSON_PATH = "peintures_tags_reference.json"


# --- Fonctions utilitaires ---
def compute_synthese_filtered(history):
    models = {"CLIP", "BLIP", "reference"}
    categories = ["tags", "genres", "styles"]
    synthese = {cat: {m: 0 for m in models} for cat in categories}

    for row in history:
        for cat in categories:
            for m in models:
                if cat == "tags":
                    if m == "reference":
                        synthese[cat][m] += len(row.get("ref_tags", []))
                    else:
                        synthese[cat][m] += sum(1 for t in row.get(m, []) if t.get("validated"))
                else:
                    validated = row.get(cat.lower(), {}).get("validated", [])
                    if m == "reference":
                        synthese[cat][m] += len(validated)
    return synthese


def compute_heatmaps_filtered(history):
    categories = ["tags", "genres", "styles"]
    models = {"CLIP", "BLIP", "reference"}
    heatmaps = {cat: {"positive": [], "negative": []} for cat in categories}

    for cat in categories:
        for row in history:
            for m in models:
                if cat == "tags":
                    ref_tags = row.get("ref_tags", [])
                    for t in ref_tags:
                        heatmaps[cat]["positive"].append({"x": m, "y": t, "v": 1})
                else:
                    vals = row.get(cat.lower(), {}).get("validated", [])
                    for v in vals:
                        heatmaps[cat]["positive"].append({"x": m, "y": v, "v": 1})
    return heatmaps


# --- Dashboard global ---
@app.route("/dashboard")
def dashboard():
    return render_template("dashboard_global.html")


# --- API dashboard ---
@app.route("/api/dashboard_data")
def api_dashboard_data():
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        history = json.load(f)

    synthese = compute_synthese_filtered(history)
    heatmaps = compute_heatmaps_filtered(history)
    models = list({"CLIP", "BLIP", "reference"})
    elements = list(
        {d["y"] for cat in ["tags", "genres", "styles"] for d in heatmaps[cat]["positive"] + heatmaps[cat]["negative"]})

    return jsonify({
        "synthese": synthese,
        "heatmaps": heatmaps,
        "models": models,
        "elements": elements,
        "history": history
    })


# --- Page ajout / validation peinture ---
@app.route("/add_painting", methods=["GET", "POST"])
def add_painting():
    if request.method == "GET":
        return render_template("add_painting.html")

    # POST : ajouter ou compléter peinture
    data = request.json
    filename = data.get("filename")
    artist = data.get("artist")
    title = data.get("title")
    tags = data.get("tags", [])
    genres = data.get("genres", [])
    styles = data.get("styles", [])

    # Charger fichier JSON
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        history = json.load(f)

    # Détection si déjà présent
    existing = next((r for r in history if r.get("filename") == filename), None)
    if existing:
        # Compléter modèles si besoin
        for model in ["CLIP", "BLIP"]:
            if model in data:
                existing[model] = data[model]
        existing["ref_tags"] = list(set(existing.get("ref_tags", []) + tags))
        existing["genre"] = {"validated": list(set(existing.get("genre", {}).get("validated", []) + genres))}
        existing["style"] = {"validated": list(set(existing.get("style", {}).get("validated", []) + styles))}
    else:
        new_row = {
            "filename": filename,
            "artist": artist,
            "title": title,
            "ref_tags": tags,
            "CLIP": data.get("CLIP", []),
            "BLIP": data.get("BLIP", []),
            "genre": {"validated": genres},
            "style": {"validated": styles}
        }
        history.append(new_row)

    # Sauvegarde
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

    return jsonify({"status": "ok", "message": "Peinture ajoutée ou mise à jour"})


if __name__ == "__main__":
    print("""path: <a href="http://127.0.0.1:5000/dashboard">Dashboard</a>""")
    app.run(debug=False)
