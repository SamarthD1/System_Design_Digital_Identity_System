from flask import Flask, jsonify
from flask_cors import CORS
from config import Config
from extensions import db, jwt, limiter
from auth import auth_bp
from user import user_bp
from admin import admin_bp
from models import Role

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize Extensions
    CORS(app)
    db.init_app(app)
    jwt.init_app(app)
    limiter.init_app(app)

    # Register Blueprints
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(user_bp, url_prefix='/api/user')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')

    # Global Error Handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return jsonify({"msg": "Resource not found"}), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return jsonify({"msg": "Internal server error"}), 500

    return app

def init_db(app):
    with app.app_context():
        db.create_all()
        # Create default roles
        admin_role = Role.query.filter_by(name='admin').first()
        if not admin_role:
            admin_role = Role(name='admin', description='Administrator with full access')
            db.session.add(admin_role)
            
        user_role = Role.query.filter_by(name='user').first()
        if not user_role:
            user_role = Role(name='user', description='Standard user')
            db.session.add(user_role)
            
        db.session.commit()
        print("Database initialized successfully.")

if __name__ == '__main__':
    app = create_app()
    init_db(app)
    app.run(host='0.0.0.0', port=5001, debug=True)
