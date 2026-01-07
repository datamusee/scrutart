from .model import Entity, Relation


def mock_graph():
    entities = {
        "wd:Q296": Entity(
            uri="https://www.wikidata.org/entity/Q296",
            label="Claude Monet",
            properties={
                "date de naissance": ["1840"],
                "nationalité": ["française"]
            }
        ),
        "wd:Q182128": Entity(
            uri="https://www.wikidata.org/entity/Q182128",
            label="Impression, soleil levant",
            properties={
                "année": ["1872"]
            }
        )
    }

    relations = [
        Relation(
            source="https://www.wikidata.org/entity/Q296",
            predicate="a peint",
            target="https://www.wikidata.org/entity/Q182128"
        )
    ]

    return entities, relations
