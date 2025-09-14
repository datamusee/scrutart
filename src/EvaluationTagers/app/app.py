# app.py
import os
import json
import requests
from functools import lru_cache

from flask import Flask, render_template, request, jsonify, send_from_directory
import pandas as pd
from PIL import Image
import io
import torch
import nltk
from nltk.corpus import wordnet as wn
from deep_translator import GoogleTranslator
import numpy as np

# Transformers models
from transformers import BlipProcessor, BlipForConditionalGeneration
from transformers import CLIPProcessor, CLIPModel

# (optionnel) sentence-transformers fallback
try:
    from sentence_transformers import SentenceTransformer
    _EMB_MODEL = SentenceTransformer('all-MiniLM-L6-v2')
except Exception:
    _EMB_MODEL = None

# --- Config paths ---
JSON_PATH = "data/peintures_tags_reference.json"
ANNOTATIONS_FILE = "data/annotations.json"
LOCAL_IMAGES_PATH = "static/images"

# --- Flask ---
app = Flask(__name__, template_folder="templates", static_folder="static")

# --- Ensure NLTK wordnet available ---
def ensure_nltk_wordnet():
    try:
        nltk.data.find('corpora/wordnet')
    except LookupError:
        nltk.download('wordnet')
    try:
        nltk.data.find('corpora/omw-1.4')
    except LookupError:
        nltk.download('omw-1.4')

ensure_nltk_wordnet()

# --- Translation cache (vers anglais) ---
@lru_cache(maxsize=2000)
def translate_to_en(text: str) -> str:
    if not text:
        return ""
    try:
        out = GoogleTranslator(source='auto', target='en').translate(text)
        return out.lower().strip()
    except Exception:
        return str(text).lower().strip()

# --- WordNet helpers ---
def get_synsets_en(word_en: str):
    if not word_en:
        return []
    try:
        syns = wn.synsets(word_en)
    except LookupError:
        nltk.download('wordnet')
        syns = wn.synsets(word_en)
    return syns or []

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

def relation_type(tag, ref_tags):
    """
    Renvoie 'exact' | 'related' | 'none'.
    Traduit en anglais, compare exact, WordNet, fallback embeddings.
    """
    if not isinstance(ref_tags, (list, tuple)):
        ref_tags = [ref_tags] if ref_tags else []
    tag_en = translate_to_en(tag)
    for ref in ref_tags:
        ref_en = translate_to_en(ref)
        # exact
        if tag_en == ref_en and tag_en != "":
            return "exact"
        # try wordnet
        tag_syns = get_synsets_en(tag_en)
        ref_syns = get_synsets_en(ref_en)
        if tag_syns and ref_syns:
            # identical synset
            if any(ts == rs for ts in tag_syns for rs in ref_syns):
                return "related"
            # hyper/hyponym relation
            for ts in tag_syns:
                for rs in ref_syns:
                    try:
                        if rs in ts.hypernyms() or rs in ts.hyponyms() or ts in rs.hypernyms() or ts in rs.hyponyms():
                            return "related"
                    except Exception:
                        continue
        # embeddings fallback
        if sem_related(tag_en, ref_en):
            return "related"
    return "none"

# --- Annotations store (JSON) ---
os.makedirs(os.path.dirname(ANNOTATIONS_FILE), exist_ok=True)
if not os.path.exists(ANNOTATIONS_FILE):
    with open(ANNOTATIONS_FILE, "w", encoding="utf-8") as f:
        json.dump([], f, ensure_ascii=False, indent=2)

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

# --- Load JSON dataset ---
with open(JSON_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

# normalize dictionary rows: ensure columns exist and empty lists, artist present
for item in data:
    item.setdefault("artist", "")
    item.setdefault("ref_tags", [])
    item.setdefault("CLIP", [])
    item.setdefault("BLIP", [])
    item.setdefault("StyleClassifier", [])
    item.setdefault("GemmArte", [])
df = pd.DataFrame(data)
df = df.fillna("")  # safety

# --- Initialize models (global) ---
device = "cuda" if torch.cuda.is_available() else "cpu"

# BLIP
try:
    blip_processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
    blip_model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base").to(device)
except Exception as e:
    blip_processor = blip_model = None
    print("[WARN] BLIP unavailable:", e)

# CLIP
try:
    clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
    clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32").to(device)
except Exception as e:
    clip_processor = clip_model = None
    print("[WARN] CLIP unavailable:", e)

def fetch_image_from_url(url):
    resp = requests.get(url, stream=True, timeout=15)
    resp.raise_for_status()
    return Image.open(io.BytesIO(resp.content)).convert("RGB")

def blip_generate_tags(image_url, max_tags=6):
    if blip_processor is None or blip_model is None:
        return []
    try:
        if image_url.startswith("http"):
            raw_image = fetch_image_from_url(image_url)
        else:
            raw_image = Image.open(os.path.join(LOCAL_IMAGES_PATH, image_url)).convert("RGB")
        inputs = blip_processor(images=raw_image, return_tensors="pt").to(device)
        out = blip_model.generate(**inputs, max_new_tokens=30)
        caption = blip_processor.decode(out[0], skip_special_tokens=True).lower()
        # simple tokenization -> keep words of length>3, remove duplicates
        toks = [t.strip() for t in caption.replace(",", " ").replace(".", " ").split() if len(t) > 3]
        # preserve order unique
        seen = set(); tags = []
        for t in toks:
            if t not in seen:
                seen.add(t); tags.append(t)
            if len(tags) >= max_tags:
                break
        return tags
    except Exception as e:
        print("[BLIP ERROR]", e)
        return []

def clip_generate_tags(image_url, candidate_tags, top_k=5):
    """Zero-shot rank of candidate_tags with CLIP. candidate_tags should be English strings."""
    if clip_processor is None or clip_model is None:
        return []
    try:
        if image_url.startswith("http"):
            raw_image = fetch_image_from_url(image_url)
        else:
            raw_image = Image.open(os.path.join(LOCAL_IMAGES_PATH, image_url)).convert("RGB")
        inputs = clip_processor(text=candidate_tags, images=raw_image, return_tensors="pt", padding=True)
        inputs = {k: v.to(device) for k, v in inputs.items()}
        with torch.no_grad():
            outputs = clip_model(**inputs)
            logits_per_image = outputs.logits_per_image  # shape (batch, text_len)
            probs = logits_per_image.softmax(dim=1).cpu().numpy()[0]
        sorted_idx = probs.argsort()[::-1]
        ranked = [candidate_tags[i] for i in sorted_idx[:top_k]]
        return [t.lower() for t in ranked]
    except Exception as e:
        print("[CLIP ERROR]", e)
        return []

# --- Helper: build candidate tags (english) from ref_tags of dataset ---
all_ref_tags = sorted({translate_to_en(t) for tags in df["ref_tags"] for t in tags})
# add some generic candidates
all_ref_tags = list(dict.fromkeys(all_ref_tags + ["boat", "person", "landscape", "portrait", "tree", "water", "house", "dog", "cat"]))

# --- Serve static local images via /images/<filename> (for local file support) ---
@app.route("/images/<path:filename>")
def serve_image(filename):
    return send_from_directory(LOCAL_IMAGES_PATH, filename)

# --- Main route ---
@app.route("/")
def index():
    query = request.args.get("q", "").lower()
    idx = int(request.args.get("idx", 0))
    # search in filename and artist
    if query:
        mask = df["filename"].str.lower().str.contains(query) | df["artist"].str.lower().str.contains(query)
        results = df[mask]
    else:
        results = df

    if results.empty:
        return "Aucune image trouvée."

    idx = max(0, min(idx, len(results) - 1))
    row = results.iloc[idx].to_dict()

    # Determine image URL (mix mode)
    if str(row["filename"]).startswith("http"):
        img_url = row["filename"]
    else:
        img_url = f"/images/{row['filename']}"

    # --- === ICI : logique qui construit 'models' pour la page ===
    # C'est l'endroit correct : 'row' existe, relation_type est défini globalement, et on peut appeler les modèles.
    models = {}
    for col in ["CLIP", "BLIP", "StyleClassifier", "GemmArte"]:
        # get existing predictions from JSON (may be string or list)
        existing = row.get(col, [])
        if isinstance(existing, str):
            # if user stored as semicolon separated string
            existing = [t.strip() for t in existing.split(";") if t.strip()]
        # if empty, generate
        if (not existing) and col == "BLIP":
            existing = blip_generate_tags(row["filename"], max_tags=6)
        if (not existing) and col == "CLIP":
            # use candidate tags in english; CLIP returns english candidates, we keep lowercase
            existing = clip_generate_tags(row["filename"], candidate_tags=all_ref_tags, top_k=6)
        # Build list of tuples (tag, relation)
        models[col] = [(t, relation_type(t, row.get("ref_tags", []))) for t in existing]

    # pass artist too
    artist = row.get("artist", "")

    return render_template("viewer.html",
                           filename=row["filename"],
                           img_url=img_url,
                           artist=artist,
                           ref_tags=row.get("ref_tags", []),
                           models=models,
                           idx=idx,
                           total=len(results),
                           query=query)

# --- validate endpoint (save to JSON) ---
@app.route("/validate", methods=["POST"])
def validate():
    data_in = request.json
    save_annotation(data_in["filename"], data_in["model"], data_in["tag"], data_in["validation"])
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
