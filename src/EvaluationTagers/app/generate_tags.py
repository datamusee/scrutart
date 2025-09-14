# generate_tags.py
import os

# Par exemple : Dossier dans lequel tu as les droits
os.environ["TRANSFORMERS_CACHE"] = "D:/cache/huggingface_cache"
os.environ["HF_HOME"] = "D:/cache/huggingface_cache"
import json
from transformers import BlipProcessor, BlipForConditionalGeneration, CLIPProcessor, CLIPModel
from PIL import Image
import requests
import torch
from deep_translator import GoogleTranslator

device = "cuda" if torch.cuda.is_available() else "cpu"

# load models
blip_processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
blip_model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base").to(device)

clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32").to(device)

def fetch_image(url_or_local):
    if str(url_or_local).startswith("http"):
        r = requests.get(url_or_local, stream=True, timeout=15)
        r.raise_for_status()
        return Image.open(r.raw).convert("RGB")
    else:
        imagepath = os.path.join("static/images/", url_or_local)
        return Image.open(imagepath).convert("RGB")

def blip_generate_tags(image_input, max_tags=6):
    inputs = blip_processor(images=image_input, return_tensors="pt").to(device)
    out = blip_model.generate(**inputs, max_new_tokens=30)
    caption = blip_processor.decode(out[0], skip_special_tokens=True).lower()
    toks = [t.strip() for t in caption.replace(",", " ").replace(".", " ").split() if len(t) > 3]
    seen = set(); tags = []
    for t in toks:
        if t not in seen:
            seen.add(t); tags.append(t)
        if len(tags) >= max_tags: break
    return tags

def clip_generate_tags(image_input, candidate_tags, top_k=6):
    inputs = clip_processor(text=candidate_tags, images=image_input, return_tensors="pt", padding=True)
    inputs = {k:v.to(device) for k,v in inputs.items()}
    with torch.no_grad():
        outputs = clip_model(**inputs)
        logits_per_image = outputs.logits_per_image
        probs = logits_per_image.softmax(dim=1).cpu().numpy()[0]
    sorted_idx = probs.argsort()[::-1]
    ranked = [candidate_tags[i] for i in sorted_idx[:top_k]]
    return [t.lower() for t in ranked]

def translate_to_en(word):
    try:
        return GoogleTranslator(source='auto', target='en').translate(word).lower()
    except Exception:
        return str(word).lower()

def process(json_path="data/peintures_tags_reference.json"):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # build candidate tags from all ref_tags translated
    all_ref = set()
    for e in data:
        for t in e.get("ref_tags", []):
            all_ref.add(translate_to_en(t))
    # add some generics
    candidates = list(all_ref) + ["boat","river","water","tree","flower","portrait","landscape","person","dog","cat"]
    candidates = list(dict.fromkeys(candidates))

    for entry in data:
        fn = entry.get("filename")
        try:
            img = fetch_image(fn)
        except Exception as e:
            print("Erreur chargement image", fn, e)
            continue

        if not entry.get("BLIP"):
            print("BLIP:", fn)
            entry["BLIP"] = blip_generate_tags(img, max_tags=6)
        if not entry.get("CLIP"):
            print("CLIP:", fn)
            entry["CLIP"] = clip_generate_tags(img, candidates, top_k=6)
        # If you want, call a style classifier here
        if not entry.get("StyleClassifier"):
            # naive placeholder
            entry["StyleClassifier"] = entry.get("StyleClassifier") or ["Unknown"]

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("Terminé — JSON mis à jour :", json_path)

if __name__ == "__main__":
    process()
