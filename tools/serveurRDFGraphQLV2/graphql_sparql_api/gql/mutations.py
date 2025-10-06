import json
from graphene import Mutation, String, Field, Boolean
from graphql import GraphQLError

def create_mutation(type_name: str, type_uri: str, sparql_client, config, schema_def):
    class TypeMutation(Mutation):
        class Arguments:
            id = String(required=True)
            data = String(required=True)
        
        success = Field(String)
        entity = Field(String)
        
        def mutate(root, info, id, data):
            try:
                data_dict = json.loads(data)
                triples = [f"<{id}> rdf:type <{type_uri}> ."]
                
                for prop, value in data_dict.items():
                    if isinstance(value, str) and value.startswith('http'):
                        triples.append(f"<{id}> <{prop}> <{value}> .")
                    else:
                        escaped = str(value).replace('"', '\\"')
                        triples.append(f'<{id}> <{prop}> "{escaped}" .')
                
                update_query = f"""
                PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
                INSERT DATA {{ {' '.join(triples)} }}
                """
                
                sparql_client.update(update_query)
                return TypeMutation(success="Created", entity=id)
            except Exception as e:
                raise GraphQLError(f"Mutation failed: {str(e)}")
    
    return TypeMutation
