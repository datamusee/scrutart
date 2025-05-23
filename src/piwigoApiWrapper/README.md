# piwigo_api

Un wrapper Python pour l'API Piwigo, avec support synchrone et asynchrone (optionnel).

## Installation

```bash
pip install .
# ou pour support async :
pip install .[async]
```

## Exemple

```python
from piwigo_api import PiwigoAPI

api = PiwigoAPI("https://example.com/piwigo", "admin", "password")
print(api.pwg_session_getStatus())
```

## Fonctionnalités

- Appels dynamiques à toutes les méthodes de l'API Piwigo
- Support des appels synchrones (par défaut)
- Support asynchrone avec `httpx` (optionnel)
- Envoi d’images via `pwg.images.addSimple`
- Logger configurable
- Tests unitaires et exemples fournis

## Générer la documentation (avec pdoc)

```bash
pip install pdoc
pdoc piwigo_api -o docs
```

Cela générera la documentation HTML dans le dossier `docs/`.