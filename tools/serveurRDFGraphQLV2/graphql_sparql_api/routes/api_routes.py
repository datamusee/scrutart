from flask import Blueprint, render_template, session, redirect

api_bp = Blueprint('api', __name__)

def init_api_routes(app):
    @api_bp.route('/')
    def home():
        current_user = session.get('user_info')
        return render_template('home.html', current_user=current_user)
    
    @api_bp.route('/docs')
    def documentation():
        return render_template('docs.html')
    
    @api_bp.route('/graphiql')
    def graphiql():
        if 'jwt_token' not in session:
            session['next'] = '/graphiql'
            return redirect('/login')
        jwt_token = session['jwt_token']
        user_info = session.get('user_info', {})
        return render_template('graphiql.html', jwt_token=jwt_token, user_info=user_info)
    
    app.register_blueprint(api_bp)
