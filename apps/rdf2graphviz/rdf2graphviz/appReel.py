from rdf2graphviz import parse_nt, render_neo4j, to_html

entities, relations = parse_nt(triples)
html = to_html(render_neo4j(entities, relations))
