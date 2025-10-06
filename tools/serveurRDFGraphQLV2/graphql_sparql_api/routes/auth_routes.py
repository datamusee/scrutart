from flask import Blueprint, redirect, session, request, jsonify

auth_bp = Blueprint('auth', __name__)

def init_auth_routes(app, oauth, google, auth_manager):
    @auth_bp.route('/login')
    def login():
        redirect_uri = request.url_root.rstrip('/') + '/auth/callback'
        return google.authorize_redirect(redirect_uri)
    
    @auth_bp.route('/auth/callback')
    def auth_callback():
        try:
            token = google.authorize_access_token()
            user_info = token.get('userinfo')
            if not user_info:
                resp = google.get('https://openidconnect.googleapis.com/v1/userinfo')
                user_info = resp.json()
            
            if user_info:
                jwt_token = auth_manager.generate_jwt({
                    'email': user_info.get('email'),
                    'name': user_info.get('name'),
                    'picture': user_info.get('picture')
                })
                session['jwt_token'] = jwt_token
                session['user_info'] = user_info
                return redirect('/graphiql')
            return jsonify({'error': 'Auth failed'}), 401
        except Exception as e:
            return jsonify({'error': str(e)}), 400
    
    @auth_bp.route('/logout')
    def logout():
        session.clear()
        return redirect('/')
    
    @auth_bp.route('/token')
    def get_token():
        if 'jwt_token' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        return jsonify({'token': session['jwt_token'], 'user': session.get('user_info', {})})
    
    app.register_blueprint(auth_bp)
