# ============================================================================
# core/authentication.py - Gestion de l'authentification
# ============================================================================

"""
Gestion de l'authentification JWT et OAuth
"""

import jwt
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, session
from typing import Dict, Optional


class AuthenticationManager:
    """Gestionnaire d'authentification"""

    def __init__(self, secret: str, expiration_hours: int = 24):
        self.secret = secret
        self.expiration_hours = expiration_hours

    def generate_jwt(self, user_info: Dict) -> str:
        """Génère un token JWT pour l'utilisateur"""
        payload = {
            'user': user_info,
            'exp': datetime.utcnow() + timedelta(hours=self.expiration_hours),
            'iat': datetime.utcnow()
        }
        return jwt.encode(payload, self.secret, algorithm='HS256')

    def verify_jwt(self, token: str) -> Optional[Dict]:
        """Vérifie et décode un token JWT"""
        try:
            return jwt.decode(token, self.secret, algorithms=['HS256'])
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    def get_token_from_request(self) -> Optional[str]:
        """Extrait le token de la requête (header ou session)"""
        # Priorité 1: Bearer token
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            return auth_header.split(' ')[1]

        # Priorité 2: Session
        if 'jwt_token' in session:
            return session['jwt_token']

        return None

    def require_auth(self, f):
        """Décorateur pour protéger les routes"""

        @wraps(f)
        def decorated_function(*args, **kwargs):
            token = self.get_token_from_request()

            if not token:
                return jsonify({'error': 'Missing or invalid authorization'}), 401

            payload = self.verify_jwt(token)
            if not payload:
                return jsonify({'error': 'Invalid or expired token'}), 401

            request.user = payload['user']
            return f(*args, **kwargs)

        return decorated_function

