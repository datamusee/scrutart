from flask import Blueprint, request, jsonify
import sys
import os

# Ajouter le répertoire parent au path pour les imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

admin_bp = Blueprint('admin', __name__)

def init_admin_routes(app, auth_manager, schema_generator, cache_manager, config, schema=None):
    @admin_bp.route('/schema/refresh', methods=['POST'])
    def refresh_schema():
        token = auth_manager.get_token_from_request()
        if not token or not auth_manager.verify_jwt(token):
            return jsonify({'error': 'Unauthorized'}), 401
        try:
            print("Génération du schéma...")
            schema = schema_generator.generate_schema()
            schema_generator.save_schema(schema)
            
            num_types = len(schema.get('auto_generated', {}))
            print(f"Schéma généré avec {num_types} types")
            
            return jsonify({
                'message': 'Schema refreshed',
                'types_detected': num_types,
                'types': list(schema.get('auto_generated', {}).keys())
            })
        except Exception as e:
            import traceback
            print(f"Erreur: {traceback.format_exc()}")
            return jsonify({'error': str(e)}), 500

    @app.route('/schema/info')
    def schema_info_improved():
        """Affiche les informations sur le schéma avec correspondances URI ↔ GraphQL"""

        try:
            schema_cache = schema_generator.load_schema_cache()
            merged = schema_generator.merge_schema_definitions(
                schema_cache.get('auto_generated', {}),
                schema_cache.get('manual', {})
            )

            types_html = ""
            for type_uri, type_info in merged.items():
                type_name = schema_generator.sanitize_name(type_info['label'])

                # Construire le tableau des propriétés avec correspondances
                props_table = """
                <table class="props-table">
                    <tr>
                        <th>Propriété RDF (URI)</th>
                        <th>Nom GraphQL</th>
                        <th>Type</th>
                        <th>Exemple</th>
                    </tr>
                """

                for prop_uri, prop_info in type_info.get('properties', {}).items():
                    graphql_name = schema_generator.sanitize_name(prop_info['label'])
                    rdf_label = prop_info['label']
                    prop_type = prop_info['type']

                    # Générer un exemple de requête
                    if prop_type == 'reference':
                        example = f'{graphql_name} {{ id }}'
                    else:
                        example = graphql_name

                    # Afficher l'URI complète et le label RDF
                    props_table += f"""
                    <tr>
                        <td>
                            <code class="uri-code">{prop_uri}</code><br>
                            <small style="color: #666;">Label: {rdf_label}</small>
                        </td>
                        <td><strong class="graphql-name">{graphql_name}</strong></td>
                        <td><span class="type-badge">{prop_type}</span></td>
                        <td><code class="example-code">{example}</code></td>
                    </tr>
                    """

                props_table += "</table>"

                # Exemple de requête complète
                example_query = f"""query {{
      get{type_name}(id: "URI_DE_L_INSTANCE") {{
        id
        {chr(10).join(['    ' + schema_generator.sanitize_name(p['label']) for p in list(type_info.get('properties', {}).values())[:5]])}
      }}
    }}"""

                example_list_query = f"""query {{
      all{type_name}s {{
        id
        {chr(10).join(['    ' + schema_generator.sanitize_name(p['label']) for p in list(type_info.get('properties', {}).values())[:3]])}
      }}
    }}"""

                # Échapper pour affichage HTML mais pas pour data-query
                # On utilise base64 pour éviter les problèmes d'échappement
                import base64
                example_query_b64 = base64.b64encode(example_query.encode()).decode()
                example_list_query_b64 = base64.b64encode(example_list_query.encode()).decode()

                types_html += f"""
                <div class="type-box">
                    <h3>
                        {type_name}
                        <span class="type-uri-badge">Type RDF</span>
                    </h3>
                    <div class="type-info">
                        <p><strong>URI RDF:</strong> <code class="uri-code">{type_uri}</code></p>
                        <p><strong>Graphes:</strong> {', '.join([f'<code class="graph-code">{g}</code>' for g in type_info.get('graphs', []) if g])}</p>
                    </div>

                    <h4>📋 Propriétés ({len(type_info.get('properties', {}))})</h4>
                    {props_table if type_info.get('properties') else '<p class="no-props">Aucune propriété détectée</p>'}

                    <details class="query-examples">
                        <summary><strong>📝 Exemples de requêtes GraphQL</strong></summary>

                        <div class="example-section">
                            <h5>Récupérer un objet spécifique:</h5>
                            <pre class="query-example">{example_query}</pre>
                            <button onclick="copyToClipboard(this)" data-query-b64="{example_query_b64}">📋 Copier</button>
                        </div>

                        <div class="example-section">
                            <h5>Liste des objets:</h5>
                            <pre class="query-example">{example_list_query}</pre>
                            <button onclick="copyToClipboard(this)" data-query-b64="{example_list_query_b64}">📋 Copier</button>
                        </div>

                        <div class="example-section">
                            <h5>Mutations disponibles:</h5>
                            <ul>
                                <li><code>create{type_name}(id: String!, data: String!)</code></li>
                                <li><code>delete{type_name}(id: String!)</code></li>
                            </ul>
                        </div>
                    </details>
                </div>
                """

            return f'''
            <!DOCTYPE html>
            <html>
            <head>
                <title>Schéma GraphQL - Documentation</title>
                <style>
                    body {{
                        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
                        max-width: 1400px;
                        margin: 20px auto;
                        padding: 20px;
                        background: #f5f5f5;
                        line-height: 1.6;
                    }}
                    h1, h2, h3, h4 {{ color: #2c3e50; }}

                    .header {{
                        background: white;
                        padding: 25px;
                        border-radius: 8px;
                        margin-bottom: 20px;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    }}

                    .type-box {{
                        background: white;
                        padding: 25px;
                        margin: 20px 0;
                        border-radius: 8px;
                        border-left: 4px solid #3498db;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    }}

                    .type-uri-badge {{
                        font-size: 12px;
                        background: #e8f5e9;
                        color: #2e7d32;
                        padding: 4px 12px;
                        border-radius: 12px;
                        font-weight: normal;
                        margin-left: 10px;
                    }}

                    .type-info {{
                        background: #f8f9fa;
                        padding: 15px;
                        border-radius: 4px;
                        margin: 15px 0;
                    }}

                    .props-table {{
                        width: 100%;
                        border-collapse: collapse;
                        margin: 15px 0;
                        background: white;
                    }}

                    .props-table th {{
                        background: #34495e;
                        color: white;
                        padding: 12px;
                        text-align: left;
                        font-weight: 600;
                    }}

                    .props-table td {{
                        padding: 12px;
                        border-bottom: 1px solid #ecf0f1;
                        vertical-align: top;
                    }}

                    .props-table tr:hover {{
                        background: #f8f9fa;
                    }}

                    .uri-code {{
                        background: #e8f5e9;
                        color: #2e7d32;
                        padding: 2px 8px;
                        border-radius: 3px;
                        font-family: "Courier New", monospace;
                        font-size: 12px;
                        word-break: break-all;
                    }}

                    .graphql-name {{
                        color: #e91e63;
                        font-family: "Courier New", monospace;
                        font-size: 14px;
                    }}

                    .graph-code {{
                        background: #fff3cd;
                        color: #856404;
                        padding: 2px 8px;
                        border-radius: 3px;
                        font-family: "Courier New", monospace;
                        font-size: 11px;
                    }}

                    .type-badge {{
                        display: inline-block;
                        background: #3498db;
                        color: white;
                        padding: 4px 10px;
                        border-radius: 12px;
                        font-size: 11px;
                        font-weight: 600;
                        text-transform: uppercase;
                    }}

                    .example-code {{
                        background: #f0f4f8;
                        color: #1976d2;
                        padding: 4px 8px;
                        border-radius: 3px;
                        font-family: "Courier New", monospace;
                        font-size: 13px;
                    }}

                    .query-examples {{
                        margin-top: 20px;
                        border: 1px solid #e0e0e0;
                        border-radius: 4px;
                        padding: 15px;
                        background: #fafafa;
                    }}

                    .query-examples summary {{
                        cursor: pointer;
                        font-weight: 600;
                        color: #1976d2;
                        padding: 5px;
                    }}

                    .query-examples summary:hover {{
                        color: #1565c0;
                    }}

                    .example-section {{
                        margin: 20px 0;
                    }}

                    .query-example {{
                        background: #263238;
                        color: #aed581;
                        padding: 15px;
                        border-radius: 4px;
                        overflow-x: auto;
                        font-family: "Courier New", monospace;
                        font-size: 13px;
                        line-height: 1.5;
                    }}

                    .no-props {{
                        color: #999;
                        font-style: italic;
                        padding: 20px;
                        text-align: center;
                        background: #f8f9fa;
                        border-radius: 4px;
                    }}

                    .btn {{
                        display: inline-block;
                        padding: 10px 20px;
                        margin: 5px;
                        background: #3498db;
                        color: white;
                        text-decoration: none;
                        border-radius: 4px;
                        cursor: pointer;
                        border: none;
                        font-size: 14px;
                        transition: background 0.3s;
                    }}

                    .btn:hover {{
                        background: #2980b9;
                    }}

                    .btn-refresh {{
                        background: #27ae60;
                    }}

                    .btn-refresh:hover {{
                        background: #229954;
                    }}

                    button[onclick^="copyToClipboard"] {{
                        background: #9c27b0;
                        color: white;
                        border: none;
                        padding: 8px 16px;
                        border-radius: 4px;
                        cursor: pointer;
                        font-size: 12px;
                        margin-top: 10px;
                    }}

                    button[onclick^="copyToClipboard"]:hover {{
                        background: #7b1fa2;
                    }}

                    .warning {{
                        background: #fff3cd;
                        border-left: 4px solid #ffc107;
                        padding: 15px;
                        margin: 15px 0;
                        border-radius: 4px;
                    }}

                    .info {{
                        background: #d1ecf1;
                        border-left: 4px solid #0c5460;
                        padding: 15px;
                        margin: 15px 0;
                        border-radius: 4px;
                    }}

                    .stats {{
                        display: grid;
                        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                        gap: 15px;
                        margin: 20px 0;
                    }}

                    .stat-box {{
                        background: #f8f9fa;
                        padding: 20px;
                        border-radius: 8px;
                        text-align: center;
                        border: 2px solid #e0e0e0;
                    }}

                    .stat-number {{
                        font-size: 36px;
                        font-weight: bold;
                        color: #3498db;
                    }}

                    .stat-label {{
                        color: #666;
                        font-size: 14px;
                        margin-top: 5px;
                    }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>📊 Schéma GraphQL - Documentation complète</h1>

                    <div class="stats">
                        <div class="stat-box">
                            <div class="stat-number">{len(merged)}</div>
                            <div class="stat-label">Types détectés</div>
                        </div>
                        <div class="stat-box">
                            <div class="stat-number">{sum(len(t.get('properties', {})) for t in merged.values())}</div>
                            <div class="stat-label">Propriétés totales</div>
                        </div>
                        <div class="stat-box">
                            <div class="stat-number">{'✓' if os.path.exists(config['SCHEMA_CACHE_FILE']) else '✗'}</div>
                            <div class="stat-label">Cache</div>
                        </div>
                    </div>

                    <div>
                        <a href="/" class="btn">🏠 Accueil</a>
                        <a href="/graphiql" class="btn">🎨 GraphiQL</a>
                        <button onclick="refreshSchema()" class="btn btn-refresh">🔄 Régénérer le schéma</button>
                        <a href="/graphs/mapping" class="btn">🔗 Graphes</a>
                    </div>
                </div>

                {'<div class="info">ℹ️ Pour régénérer le schéma, vous devez être authentifié.</div>' if len(merged) == 0 else ''}

                {types_html if types_html else '<div class="warning">⚠️ Aucun type RDF détecté. Cliquez sur "Régénérer le schéma" pour scanner votre endpoint SPARQL.</div>'}

                <script>
                    function refreshSchema() {{
                        if (confirm('Régénérer le schéma depuis l\\'endpoint SPARQL ?')) {{
                            fetch('/schema/refresh', {{
                                method: 'POST',
                                credentials: 'include',
                                headers: {{
                                    'Content-Type': 'application/json'
                                }}
                            }})
                            .then(r => {{
                                if (r.status === 401) {{
                                    alert('Vous devez être authentifié. Redirection vers la page de connexion...');
                                    window.location.href = '/login';
                                    return null;
                                }}
                                return r.json();
                            }})
                            .then(data => {{
                                if (data) {{
                                    alert('Schéma régénéré: ' + data.types_detected + ' types détectés');
                                    location.reload();
                                }}
                            }})
                            .catch(err => {{
                                alert('Erreur: ' + err);
                                console.error(err);
                            }});
                        }}
                    }}

                    function copyToClipboard(button) {{
                        // Décoder le base64 pour obtenir la vraie requête avec retours à la ligne
                        const queryB64 = button.getAttribute('data-query-b64');
                        const query = atob(queryB64);

                        navigator.clipboard.writeText(query).then(() => {{
                            const originalText = button.textContent;
                            button.textContent = '✓ Copié!';
                            button.style.background = '#4caf50';
                            setTimeout(() => {{
                                button.textContent = originalText;
                                button.style.background = '#9c27b0';
                            }}, 2000);
                        }}).catch(err => {{
                            alert('Erreur de copie: ' + err);
                        }});
                    }}
                </script>
            </body>
            </html>
            '''
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            print(f"Erreur dans /schema/info: {error_detail}")

            return f'''
            <!DOCTYPE html>
            <html>
            <head><title>Erreur</title></head>
            <body>
                <h1>Erreur</h1>
                <p>{str(e)}</p>
                <pre>{error_detail}</pre>
                <a href="/">Retour à l'accueil</a>
            </body>
            </html>
            ''', 500

    @admin_bp.route('/schema/info_ex')
    def schema_info_ex():
        try:
            schema_cache = schema_generator.load_schema_cache()
            merged = schema_generator.merge_schema_definitions(
                schema_cache.get('auto_generated', {}),
                schema_cache.get('manual', {})
            )

            types_html = ""
            for type_uri, type_info in merged.items():
                type_name = schema_generator.sanitize_name(type_info['label'])
                props_html = ""
                
                for prop_uri, prop_info in type_info.get('properties', {}).items():
                    prop_name = schema_generator.sanitize_name(prop_info['label'])
                    props_html += f"<li><strong>{prop_name}</strong>: {prop_info['type']}</li>"
                
                if not props_html:
                    props_html = "<li>Aucune propriété détectée</li>"
                
                types_html += f'''
                <div style="background: white; padding: 20px; margin: 15px 0; border-radius: 8px; border-left: 4px solid #3498db;">
                    <h3>{type_name}</h3>
                    <p><small>URI: {type_uri}</small></p>
                    <p><strong>Propriétés:</strong></p>
                    <ul>{props_html}</ul>
                    <div style="background: #f8f9fa; padding: 10px; margin: 10px 0; border-radius: 4px;">
                        <strong>Requêtes disponibles:</strong>
                        <ul>
                            <li><code>get{type_name}(id: String!)</code></li>
                            <li><code>all{type_name}s</code></li>
                        </ul>
                    </div>
                </div>
                '''
            
            if not types_html:
                types_html = '''
                <div style="background: #fff3cd; padding: 15px; border-radius: 4px; border-left: 4px solid #ffc107;">
                    <p>⚠️ Aucun type RDF détecté. Cliquez sur "Régénérer le schéma" pour scanner votre endpoint SPARQL.</p>
                </div>
                '''
            
            html = f'''
            <!DOCTYPE html>
            <html>
            <head>
                <title>Schéma GraphQL - Info</title>
                <style>
                    body {{ font-family: Arial, sans-serif; max-width: 1200px; margin: 20px auto; padding: 20px; background: #f5f5f5; }}
                    h1 {{ color: #2c3e50; }}
                    .header {{ background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                    .btn {{ display: inline-block; padding: 10px 20px; margin: 5px; background: #3498db; color: white; text-decoration: none; border-radius: 4px; cursor: pointer; border: none; }}
                    .btn:hover {{ opacity: 0.9; }}
                    code {{ background: #e8f5e9; padding: 2px 6px; border-radius: 3px; font-family: monospace; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>📊 Schéma GraphQL - Informations</h1>
                    <p><strong>Types détectés:</strong> {len(merged)}</p>
                    <div>
                        <a href="/" class="btn">🏠 Accueil</a>
                        <a href="/graphiql" class="btn">🎨 GraphiQL</a>
                        <button onclick="refreshSchema()" class="btn" style="background: #27ae60;">🔄 Régénérer le schéma</button>
                    </div>
                </div>
                
                {types_html}
                
                <script>
                function refreshSchema() {{
                    if (confirm("Régénérer le schéma depuis l\'endpoint SPARQL ?")) {{
                        fetch('/schema/refresh', {{
                            method: 'POST',
                            credentials: 'include'
                        }})
                        .then(r => {{
                            if (r.status === 401) {{
                                alert('Vous devez être authentifié');
                                window.location.href = '/login';
                                return null;
                            }}
                            return r.json();
                        }})
                        .then(data => {{
                            if (data) {{
                                alert('Schéma régénéré: ' + data.types_detected + ' types');
                                location.reload();
                            }}
                        }})
                        .catch(err => alert('Erreur: ' + err));
                    }}
                }}
                </script>
            </body>
            </html>
            '''
            
            return html
            
        except Exception as e:
            import traceback
            return f"<h1>Erreur</h1><pre>{traceback.format_exc()}</pre>", 500
    
    @admin_bp.route('/cache/clear', methods=['POST'])
    def clear_cache():
        token = auth_manager.get_token_from_request()
        if not token or not auth_manager.verify_jwt(token):
            return jsonify({'error': 'Unauthorized'}), 401
        cache_manager.clear()
        return jsonify({'message': 'Cache cleared'})
    
    app.register_blueprint(admin_bp)
