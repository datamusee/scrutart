import json
import sys
from pathlib import Path
import copy

MAX_EXAMPLES = 3  # Nombre maximal d'exemples réels par champ


def merge_type_labels(*types):
    """Fusionne des étiquettes de type pouvant être des str ou des listes."""
    flat = set()
    for t in types:
        if isinstance(t, list):
            flat.update(t)
        else:
            flat.add(t)
    return sorted(flat, key=str)


def merge_type_info(existing, new_info):
    """Fusionne deux structures de description, en évitant les cycles."""
    if not existing:
        return copy.deepcopy(new_info)
    if not new_info:
        return existing

    # Fusion de deux "feuilles" typées
    if isinstance(existing, dict) and isinstance(new_info, dict):
        if set(existing.keys()) >= {"type", "examples", "count"} and set(new_info.keys()) >= {"type", "examples", "count"}:
            t_existing, t_new = existing["type"], new_info["type"]

            # Si un type est "null", on garde le non-null
            if t_existing == "null" and t_new != "null":
                return copy.deepcopy(new_info)
            if t_new == "null" and t_existing != "null":
                return existing

            # Même type → fusion
            if t_existing == t_new:
                merged_examples = list(dict.fromkeys(existing["examples"] + new_info["examples"]))[:MAX_EXAMPLES]
                return {
                    "type": t_existing,
                    "examples": merged_examples,
                    "count": existing["count"] + new_info["count"]
                }

            # Types différents → cumul
            merged_types = merge_type_labels(t_existing, t_new)
            merged_examples = list(dict.fromkeys(existing["examples"] + new_info["examples"]))[:MAX_EXAMPLES]
            return {
                "type": merged_types,
                "examples": merged_examples,
                "count": existing["count"] + new_info["count"]
            }

        # Si ce sont des structures internes
        merged = copy.deepcopy(existing)
        for k, v in new_info.items():
            merged[k] = merge_type_info(merged.get(k), v)
        return merged

    # Listes
    elif isinstance(existing, list) and isinstance(new_info, list):
        if existing and new_info:
            merged = merge_type_info(existing[0], new_info[0])
            return [merged]
        return existing or new_info

    return existing


def type_summary(value, depth=0, max_depth=3):
    """Analyse un élément pour déterminer sa structure et ses exemples."""
    if depth > max_depth:
        return "..."

    if isinstance(value, dict):
        summary = {}
        for k, v in value.items():
            summary[k] = type_summary(v, depth + 1, max_depth)
        return summary

    elif isinstance(value, list):
        if not value:
            return []
        merged = None
        for item in value:
            merged = merge_type_info(merged, type_summary(item, depth + 1, max_depth))
        return [merged]

    # Valeur terminale
    val_type = (
        "str" if isinstance(value, str)
        else "int" if isinstance(value, int)
        else "float" if isinstance(value, float)
        else "bool" if isinstance(value, bool)
        else "null" if value is None
        else str(type(value).__name__)
    )
    return {"type": val_type, "examples": [value], "count": 1}


def accumulate_structure(data_list):
    """Fusionne la structure de tous les objets d'une liste."""
    merged = None
    total = len(data_list)

    for item in data_list:
        merged = merge_type_info(merged, type_summary(item))

    # Calcul du taux de présence
    add_presence_percent(merged, total)
    return merged


def add_presence_percent(structure, total):
    """Ajoute la clé 'presence' (%) pour chaque champ, récursivement."""
    if isinstance(structure, dict):
        if "count" in structure and "type" in structure:
            structure["presence"] = round(100 * structure["count"] / total, 1)
            del structure["count"]
        else:
            for v in structure.values():
                add_presence_percent(v, total)
    elif isinstance(structure, list) and structure:
        add_presence_percent(structure[0], total)


def describe_json(filepath):
    """Analyse complète d’un JSON pour en extraire structure, exemples réels et taux de présence."""
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Fichier introuvable : {filepath}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)[:1000]

    if isinstance(data, list):
        merged = accumulate_structure(data)
    else:
        merged = type_summary(data)
        add_presence_percent(merged, 1)

    print("=== Carte de structure typée avec exemples réels et taux de présence ===\n")
    print(json.dumps(merged, indent=2, ensure_ascii=False))
    print("\n✅ Analyse terminée sans récursion.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage : python {Path(__file__).name} fichier.json")
        sys.exit(1)

    describe_json(sys.argv[1])
