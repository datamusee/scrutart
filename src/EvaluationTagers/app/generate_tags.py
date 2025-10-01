import os
import io
import json
from pathlib import Path
from urllib.parse import unquote

import requests
from PIL import Image, UnidentifiedImageError
import unicodedata

import torch
from transformers import (
    BlipProcessor, BlipForConditionalGeneration,
    CLIPProcessor, CLIPModel
)

# -------------------------------------------------------------------
# Configuration
# -------------------------------------------------------------------
JSON_FILE = "data/peintures_tags_reference.json"
LOCAL_IMAGES_DIR = Path(__file__).resolve().parent / "static" / "images"
CACHE_DIR = "D:/cache/huggingface_cache"   # change ici si tu veux un autre chemin

device = "cuda" if torch.cuda.is_available() else "cpu"

# -------------------------------------------------------------------
# Fetch image (robuste)
# -------------------------------------------------------------------
def _same_basename_ignore_case_and_accents(name_a, name_b):
    na = unicodedata.normalize("NFKD", name_a).encode("ascii", "ignore").decode("ascii").lower()
    nb = unicodedata.normalize("NFKD", name_b).encode("ascii", "ignore").decode("ascii").lower()
    return na == nb

def fetch_image(url_or_local):
    """
    Renvoie un PIL.Image (RGB) depuis une URL http(s) ou un fichier local.
    Gère les noms encodés (%XX), accents et casse.
    """
    s = str(url_or_local)

    # Cas URL distante
    if s.startswith("http://") or s.startswith("https://"):
        try:
            headers = {
                "User-Agent": "Scrutart 1.1.1"
            }
            r = requests.get(s, headers=headers, timeout=20)
            r.raise_for_status()
            img = Image.open(io.BytesIO(r.content))
            return img.convert("RGB")
        except Exception as e:
            raise RuntimeError(f"Erreur ouverture image URL {s}: {e}")

    # Cas chemin local (direct ou relatif)
    p = Path(s)
    if not p.is_absolute():
        p = LOCAL_IMAGES_DIR / s

    if p.exists():
        return Image.open(p).convert("RGB")

    # Tentative avec nom décodé
    decoded = unquote(os.path.basename(s))
    p2 = LOCAL_IMAGES_DIR / decoded
    if p2.exists():
        return Image.open(p2).convert("RGB")

    # Recherche approximative (ignorer accents et casse)
    for cand in LOCAL_IMAGES_DIR.iterdir():
        if _same_basename_ignore_case_and_accents(cand.name, decoded):
            return Image.open(cand).convert("RGB")

    raise FileNotFoundError(f"Image introuvable: {s}")

# -------------------------------------------------------------------
# Modèles
# -------------------------------------------------------------------
print("Chargement BLIP...")
blip_processor = BlipProcessor.from_pretrained(
    "Salesforce/blip-image-captioning-base",
    cache_dir=CACHE_DIR
)
blip_model = BlipForConditionalGeneration.from_pretrained(
    "Salesforce/blip-image-captioning-base",
    cache_dir=CACHE_DIR
).to(device)

print("Chargement CLIP...")
clip_processor = CLIPProcessor.from_pretrained(
    "openai/clip-vit-base-patch32",
    cache_dir=CACHE_DIR
)
clip_model = CLIPModel.from_pretrained(
    "openai/clip-vit-base-patch32",
    cache_dir=CACHE_DIR
).to(device)

# -------------------------------------------------------------------
# Fonctions de tagging
# -------------------------------------------------------------------
def blip_generate_tags_from_pil(image, max_tags=6):
    inputs = blip_processor(images=image, return_tensors="pt").to(device)
    out = blip_model.generate(**inputs)
    caption = blip_processor.decode(out[0], skip_special_tokens=True)
    # Découper le caption en pseudo-tags
    return caption.lower().replace(".", "").split()[:max_tags]

def clip_generate_tags_from_pil(image, candidate_tags=None, top_k=5):
    if candidate_tags is None:
        candidate_tags = ["boat", "river", "flowers", "water", "sky", "portrait", "landscape"]

    inputs = clip_processor(
        text=candidate_tags,
        images=image,
        return_tensors="pt",
        padding=True
    ).to(device)

    outputs = clip_model(**inputs)
    logits_per_image = outputs.logits_per_image
    probs = logits_per_image.softmax(dim=1).cpu().detach().numpy()[0]

    scored = list(zip(candidate_tags, probs))
    scored.sort(key=lambda x: -x[1])
    return [t for t, p in scored[:top_k]]

# -------------------------------------------------------------------
# Boucle principale
# -------------------------------------------------------------------
def main():
    with open(JSON_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    for entry in data:
        fname = entry["filename"]
        try:
            img = fetch_image(fname)
        except Exception as e:
            print("❌ Impossible d’ouvrir:", fname, "|", e)
            continue

        print("▶ Traitement:", fname)

        try:
            entry["BLIP"] = blip_generate_tags_from_pil(img)
            print("  BLIP:", entry["BLIP"])
        except Exception as e:
            print("  ⚠ Erreur BLIP:", e)

        try:
            entry["CLIP"] = clip_generate_tags_from_pil(img)
            print("  CLIP:", entry["CLIP"])
        except Exception as e:
            print("  ⚠ Erreur CLIP:", e)

    # Sauvegarde
    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print("✅ Mise à jour de", JSON_FILE, "terminée.")

if __name__ == "__main__":
    main()
