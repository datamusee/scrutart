from rdf2graphviz import mock_graph, render_neo4j, to_html

entities, relations = mock_graph()
html = to_html(render_neo4j(entities, relations))
