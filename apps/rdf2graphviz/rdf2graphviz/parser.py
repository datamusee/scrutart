from rdflib import Graph, URIRef, Literal, RDFS
from .model import Entity, Relation
from .labels import get_best_label, local_name


def parse_nt(triples: list[str]):
    g = Graph()
    for t in triples:
        g.parse(data=t, format="nt")
    return from_graph(g)


def from_graph(g: Graph):
    entities = {}
    relations = []

    for s, p, o in g:
        if not isinstance(s, URIRef):
            continue

        s_uri = str(s)
        entities.setdefault(
            s_uri,
            Entity(uri=s_uri, label=get_best_label(g, s))
        )

        if isinstance(o, URIRef):
            o_uri = str(o)
            entities.setdefault(
                o_uri,
                Entity(uri=o_uri, label=get_best_label(g, o))
            )
            relations.append(
                Relation(
                    source=s_uri,
                    predicate=local_name(str(p)),
                    target=o_uri
                )
            )
        elif isinstance(o, Literal):
            entities[s_uri].properties.setdefault(
                local_name(str(p)), []
            ).append(str(o))

    return entities, relations
