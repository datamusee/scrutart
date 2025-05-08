
import csv

def load_creator_data_from_csv(path):
    with open(path, newline='', encoding='utf-8') as f:
        return [(int(row["category_id"]), row["name"], row["slug"]) for row in csv.DictReader(f)]
