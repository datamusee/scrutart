from flask import Flask, render_template, request, jsonify
import pandas as pd
import json
import os
from nltk.corpus import wordnet as wn

from transformers import BlipProcessor, BlipForConditionalGeneration
from PIL import Image
import requests
import torch

# Charger BLIP une seule fois au démarrage
device = "cuda" if torch.cuda.is_available() else "cpu"
blip_processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
blip_model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base").to(device)

def blip_generate_tags(image_url, max_tags=5):
    try:
        raw_image = Image.open(requests.get(image_url, stream=True).raw).convert("RGB")
        inputs = blip_processor(raw_image, return_tensors="pt").to(device)
        out = blip_model.generate(**inputs, max_new_tokens=30)
        caption = blip_processor.decode(out[0], skip_special_tokens=True)
        # on découpe la légende en tags naïfs
        tags = [w.strip().lower() for w in caption.replace(",", "").split(" ") if len(w) > 3]
        return tags[:max_tags]
    except Exception as e:
        print(f"[BLIP ERROR] {e}")
        return []

app = Flask(__name__)

# === CONFIG ===
JSON_PATH = "data/peintures_tags_reference.json"
IMAGES_PATH = "static/images"
ANNOTATIONS_FILE = "data/annotations.json"

# Charger JSON → DataFrame
with open(JSON_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

# Normaliser en DataFrame
df = pd.DataFrame(data)
print("dataframe head", df.head())

# Assurer que chaque champ tags est une liste
for col in df.columns:
    if col not in ["filename", "artist"]:
        df[col] = df[col].apply(lambda x: x if isinstance(x, list) else [])


# === Annotation store ===
if not os.path.exists(ANNOTATIONS_FILE):
    with open(ANNOTATIONS_FILE, "w", encoding="utf-8") as f:
        json.dump([], f)

def save_annotation(filename, model, tag, validation):
    with open(ANNOTATIONS_FILE, "r+", encoding="utf-8") as f:
        annotations = json.load(f)
        annotations.append({
            "filename": filename,
            "model": model,
            "tag": tag,
            "validation": validation
        })
        f.seek(0)
        json.dump(annotations, f, indent=2, ensure_ascii=False)
        f.truncate()

# === Matching logique ===
from deep_translator import GoogleTranslator
from functools import lru_cache
from nltk.corpus import wordnet as wn

# === Traduction avec cache ===
# Dépendances (installer si besoin) :
# pip install deep-translator nltk sentence-transformers

import nltk
from nltk.corpus import wordnet as wn
from deep_translator import GoogleTranslator
from functools import lru_cache
import numpy as np

# (Optionnel) embeddings fallback
try:
    from sentence_transformers import SentenceTransformer
    _EMB_MODEL = SentenceTransformer('all-MiniLM-L6-v2')
except Exception:
    _EMB_MODEL = None

# --- s'assurer que les corpus NLTK sont disponibles ---
def ensure_nltk_wordnet():
    try:
        nltk.data.find('corpora/wordnet')
    except LookupError:
        nltk.download('wordnet')
    # omw-1.4 fournit les traductions/lemmas multilingues
    try:
        nltk.data.find('corpora/omw-1.4')
    except LookupError:
        nltk.download('omw-1.4')

ensure_nltk_wordnet()

# --- traduction avec cache (évite les appels répétés) ---
@lru_cache(maxsize=2000)
def translate_to_en(word: str) -> str:
    if not word:
        return ""
    w = str(word).strip()
    try:
        # auto -> en
        out = GoogleTranslator(source='auto', target='en').translate(w)
        return out.lower()
    except Exception:
        # fallback : renvoyer la chaîne d'origine en minuscule
        return w.lower()

# --- obtenir synsets de façon robuste ---
def get_synsets_en(word_en: str):
    if not word_en:
        return []
    w = str(word_en).strip().lower()
    try:
        syns = wn.synsets(w)  # anglais par défaut
    except LookupError:
        # essayer de retélécharger et réessayer
        nltk.download('wordnet')
        syns = wn.synsets(w)
    return syns or []

# --- similarité sémantique fallback (si embeddings dispo) ---
def sem_related(a: str, b: str, thresh: float = 0.72) -> bool:
    if _EMB_MODEL is None or not a or not b:
        return False
    try:
        emb = _EMB_MODEL.encode([a, b], convert_to_numpy=True)
        a_v, b_v = emb[0], emb[1]
        denom = (np.linalg.norm(a_v) * np.linalg.norm(b_v))
        if denom == 0:
            return False
        sim = float(np.dot(a_v, b_v) / denom)
        return sim >= thresh
    except Exception:
        return False

# --- relation_type robuste ---
def relation_type(tag, ref_tags):
    """
    Retourne : 'exact' | 'related' | 'none'
    - traduit les deux côtés en anglais
    - vérifie égalité exacte (après traduction)
    - teste synset identique / hypernym / hyponym
    - fallback sur embeddings si aucun synset trouvé
    """
    try:
        tag_en = translate_to_en(tag)
    except Exception:
        tag_en = str(tag).lower()

    # si ref_tags peut être une chaîne, normaliser en liste
    if not isinstance(ref_tags, (list, tuple)):
        ref_tags = [ref_tags] if ref_tags else []

    for ref in ref_tags:
        try:
            ref_en = translate_to_en(ref)
        except Exception:
            ref_en = str(ref).lower()

        # exact après traduction
        if tag_en == ref_en and tag_en != "":
            return "exact"

        # récupérer synsets
        tag_syns = get_synsets_en(tag_en)
        ref_syns = get_synsets_en(ref_en)

        # si on a des synsets des deux côtés, tester correspondances WordNet
        if tag_syns and ref_syns:
            # si un synset identique => related (on peut considérer exact au-dessus déjà)
            if any(ts == rs for ts in tag_syns for rs in ref_syns):
                return "related"
            # hyper/hyponyme check (les hypernyms()/hyponyms() renvoient des synsets)
            for ts in tag_syns:
                for rs in ref_syns:
                    try:
                        if rs in ts.hypernyms() or rs in ts.hyponyms() or ts in rs.hypernyms() or ts in rs.hyponyms():
                            return "related"
                    except Exception:
                        # ignorer erreurs sur relation synset individuelle
                        continue

        # si pas de synsets significatifs, utiliser fallback sémantique (embeddings)
        if sem_related(tag_en, ref_en):
            return "related"

    # rien trouvé pour aucun ref
    return "none"

# === Routes ===
@app.route("/")
def index():
    query = request.args.get("q", "").lower()
    idx = int(request.args.get("idx", 0))

    if query:
        results = df[
            df["filename"].str.lower().str.contains(query)
            | df["artist"].str.lower().str.contains(query)
        ]
    else:
        results = df

    if results.empty:
        return "Aucune image trouvée."

    idx = max(0, min(idx, len(results) - 1))
    row = results.iloc[idx]

    # Déterminer l’URL de l’image
    if str(row["filename"]).startswith("http"):
        img_url = row["filename"]
    else:
        img_url = f"/static/images/{row['filename']}"

    # Construire dict des modèles
    models = {}
    for col in df.columns:
        if col not in ["filename", "ref_tags", "artist"]:
            tags = []
            for tag in row[col]:
                rel = relation_type(tag, row["ref_tags"])
                tags.append((tag, rel))
            models[col] = tags

    return render_template(
        "viewer.html",
        filename=row["filename"],
        img_url=img_url,
        artist=row["artist"],  # <── ajout
        ref_tags=row["ref_tags"],
        models=models,
        idx=idx,
        total=len(results),
        query=query,
    )

@app.route("/validate", methods=["POST"])
def validate():
    data = request.json
    save_annotation(data["filename"], data["model"], data["tag"], data["validation"])
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(debug=False)
