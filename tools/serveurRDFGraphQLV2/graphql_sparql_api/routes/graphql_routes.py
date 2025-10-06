from flask import Blueprint, request, jsonify, session

graphql_bp = Blueprint('graphql', __name__)


def init_graphql_routes(app, auth_manager, schema_generator, jobs, results_dir, schema=None):
    @app.route('/graphql', methods=['POST', 'GET'])
    def graphql_endpoint():
        """Endpoint GraphQL principal avec support complet"""

        # Vérifier l'authentification (session ou token Bearer)
        jwt_token = None

        ####################### FROM Claude v15
        #token = auth_manager.get_token_from_request()
        #if not token or not auth_manager.verify_jwt(token):
        #    return jsonify({'error': 'Unauthorized'}), 401
        #######################

        # Priorité 1: Token Bearer dans le header (pour les appels API)
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            jwt_token = auth_header.split(' ')[1]

        # Priorité 2: Session (pour GraphiQL)
        elif 'jwt_token' in session:
            jwt_token = session['jwt_token']

        # Si pas de token trouvé
        if not jwt_token:
            return jsonify({'error': 'Missing or invalid authorization'}), 401

        # Vérifier le token
        payload = auth_manager.verify_jwt(token=jwt_token)
        if not payload:
            return jsonify({'error': 'Invalid or expired token'}), 401

        try:
            # Récupérer le VRAI schéma GraphQL (pas le cache JSON)
            if not vars().get('graphql_schema'):
                graphql_schema = schema
            if graphql_schema is None:
                graphql_schema = schema_generator.build_graphql_schema(schema_generator) #build_complete_graphql_schema()

            if graphql_schema is None:
                return jsonify({
                    'errors': [{
                        'message': 'GraphQL schema not initialized. Please refresh the schema at /schema/refresh'
                    }]
                }), 500

            # Traiter la requête
            if request.method == 'POST':
                data = request.get_json()
                if not data:
                    return jsonify({'error': 'No JSON data provided'}), 400

                query = data.get('query')
                variables = data.get('variables') or {}
                operation_name = data.get('operationName')
            else:
                query = request.args.get('query')
                variables = {}
                operation_name = None

            if not query:
                return jsonify({'error': 'No query provided'}), 400

            print(f"\n{'=' * 60}")
            print(f"GraphQL Query: {query}")
            print(f"Variables: {variables}")
            print(f"{'=' * 60}\n")
            use_cache = data.get('use_cache', False)  # ✅ Cache non activé par défaut

            # Exécuter la requête avec le schéma Graphene
            result = graphql_schema.execute(
                query,
                variable_values=variables,
                operation_name=operation_name,
                context_value={
                    'user': auth_manager.verify_jwt(jwt_token)['user'],
                    'use_cache': use_cache  # ✅ Passer use_cache au contexte
                }
            )

            response_data = {}

            if result.data is not None:
                response_data['data'] = result.data
                print(f"✓ Data: {result.data}")

            if result.errors:
                print(f"⚠️ Errors: {result.errors}")
                response_data['errors'] = [
                    {
                        'message': str(e),
                        'locations': [{'line': loc.line, 'column': loc.column} for loc in e.locations] if hasattr(e,
                                                                                                                  'locations') and e.locations else None,
                        'path': list(e.path) if hasattr(e, 'path') and e.path else None
                    }
                    for e in result.errors
                ]

            return jsonify(response_data)

        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            print(f"❌ Error: {error_detail}")

            return jsonify({
                'errors': [{
                    'message': str(e),
                    'type': type(e).__name__
                }]
            }), 500

    app.register_blueprint(graphql_bp)

