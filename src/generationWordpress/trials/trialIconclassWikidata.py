import json
from SPARQLWrapper import SPARQLWrapper, JSON
import requests

# SPARQL endpoint for Iconclass
def get_iconclass_label(iconclass_notation, lang="fr"):
    
    return None

# Function to search for a corresponding Wikidata entity
def search_wikidata_entity(label):
    url = "https://www.wikidata.org/w/api.php"
    params = {
        "action": "wbsearchentities",
        "search": label,
        "language": "en",
        "format": "json"
    }

    response = requests.get(url, params=params)
    data = response.json()

    if "search" in data:
        return [
            {
                "id": item["id"],
                "label": item.get("label", "N/A"),
                "description": item.get("description", "N/A")
            }
            for item in data["search"]
        ]

    return None

# Load or initialize the JSON file
def load_json(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

def save_json(file_path, data):
    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)

# Main function
def main():
    json_file = "iconclass_data.json"
    data = load_json(json_file)

    iconclass_notation = input("Enter the Iconclass notation: ")

    # Check if the notation exists in the JSON file and if it's validated
    if iconclass_notation in data:
        entry = data[iconclass_notation]
        if entry.get("checked") is True:
            print(f"This notation is already validated: {entry}")
            return

    label = get_iconclass_label(iconclass_notation)

    if label:
        print(f"Label found: {label}")
        entities = search_wikidata_entity(label)

        if entities:
            print("\nPossible matching Wikidata entities:")
            for entity in entities:
                print(f"ID: {entity['id']}, Label: {entity['label']}, Description: {entity['description']}")

            # Update the JSON data
            data[iconclass_notation] = {
                "uri": entities[0]["id"],
                "label": {"en": label},
                "checked": False
            }
            print(f"Saved the first entity as: {entities[0]['id']}")
        else:
            print("No matching Wikidata entities found.")
    else:
        print("No label found for the given Iconclass notation.")

    save_json(json_file, data)

if __name__ == "__main__":
    main()
