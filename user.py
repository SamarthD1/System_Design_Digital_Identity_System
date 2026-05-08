from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from models import User, db
from utils import generate_mfa_secret, get_mfa_uri, generate_qr_code_base64, verify_mfa_token

user_bp = Blueprint('user', __name__)

@user_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    if not user:
        return jsonify({"msg": "User not found"}), 404
        
    return jsonify({
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "mfa_enabled": user.mfa_enabled,
        "roles": [r.name for r in user.roles],
        "created_at": user.created_at.isoformat()
    }), 200

@user_bp.route('/mfa/setup', methods=['POST'])
@jwt_required()
def setup_mfa():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if user.mfa_enabled:
        return jsonify({"msg": "MFA is already enabled"}), 400
        
    secret = generate_mfa_secret()
    user.mfa_secret = secret
    db.session.commit()
    
    uri = get_mfa_uri(secret, user.email)
    qr_code = generate_qr_code_base64(uri)
    
    return jsonify({
        "secret": secret,
        "qr_code": qr_code,
        "msg": "Scan the QR code with your authenticator app and verify the token to enable MFA."
    }), 200

@user_bp.route('/mfa/enable', methods=['POST'])
@jwt_required()
def enable_mfa():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    data = request.get_json()
    token = data.get('token')
    
    if not token:
        return jsonify({"msg": "Token is required"}), 400
        
    if not user.mfa_secret:
        return jsonify({"msg": "MFA setup not initiated"}), 400
        
    if verify_mfa_token(user.mfa_secret, token):
        user.mfa_enabled = True
        db.session.commit()
        return jsonify({"msg": "MFA enabled successfully"}), 200
    else:
        return jsonify({"msg": "Invalid token"}), 400
