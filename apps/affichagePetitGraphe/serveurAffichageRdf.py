from flask import Flask, render_template, request, jsonify, url_for, redirect
import re
import json

app = Flask(__name__)

def parse_triples(triples_text):
    triples = []
    for line in triples_text.split('\n'):
        line = line.strip()
        if line and '.' in line:
            parts = line.split('.')[0].split()
            if len(parts) >= 3:
                s, p = parts[0], parts[1]
                o = ' '.join(parts[2:])
                triples.append((s, p, o))
    return triples

def generate_d3_data(triples, mode):
    nodes = set()
    links = []
    node_props = {}

    for s, p, o in triples:
        nodes.add(s)
        if not (o.startswith('"') or re.match(r'^\d+$', o.replace('-', ''))):
            nodes.add(o)
            links.append({"source": s, "target": o, "label": p, "type": "link"})
        else:
            if s not in node_props:
                node_props[s] = []
            literal_value = o.replace('"', '').replace('@fr', ' (fr)').replace('@en', ' (en)')
            node_props[s].append({"property": p, "value": literal_value})

    d3_nodes = []
    for node in nodes:
        d3_nodes.append({"id": node, "type": "entity"})

    if mode == "cartouches":
        for entity, props in node_props.items():
            d3_nodes.append({"id": f"{entity}_props", "type": "literal_group", "entity": entity, "properties": props})

    return {"nodes": d3_nodes, "links": links, "node_props": node_props}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/graph_only')
def graph_only():
    return render_template('graph_only.html')

@app.route('/generate', methods=['POST'])
def generate():
    triples_text = request.form['triples']
    mode = request.form['mode']
    triples = parse_triples(triples_text)
    data = generate_d3_data(triples, mode)
    return jsonify(data)

@app.route('/generate_and_redirect', methods=['POST'])
def generate_and_redirect():
    triples_text = request.form['triples']
    mode = request.form['mode']
    triples = parse_triples(triples_text)
    data = generate_d3_data(triples, mode)
    data_json = json.dumps(data)
    return redirect(url_for('display_graph_only', data=data_json, mode=mode))

@app.route('/display_graph_only')
def display_graph_only():
    data_json = request.args.get('data')
    mode = request.args.get('mode')
    return render_template('graph_only.html', data=data_json, mode=mode)

if __name__ == '__main__':
    app.run(debug=False)
