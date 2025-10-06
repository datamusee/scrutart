from graphene import String, Int, Float, DateTime

def graphql_type_from_rdf_type(rdf_type: str) -> type:
    mapping = {
        'string': String,
        'int': Int,
        'float': Float,
        'datetime': DateTime,
        'date': String,
        'reference': String
    }
    return mapping.get(rdf_type, String)
