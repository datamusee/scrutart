"""Point d'entrée pour Passenger (« Setup Python App » de cPanel / o2switch)."""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from app import creer_app  # noqa: E402

application = creer_app()
