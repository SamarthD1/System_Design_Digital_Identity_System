from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token, create_refresh_token,
    get_jwt_identity, jwt_required, get_jwt, decode_token
)
from models import User, Session, Role
from extensions import db, limiter
from utils import generate_password_hash, check_password_hash, verify_mfa_token
import datetime
from datetime import timezone

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
@limiter.limit("5 per minute")
def register():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    if not username or not email or not password:
        return jsonify({"msg": "Missing required fields"}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({"msg": "Username already exists"}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({"msg": "Email already exists"}), 400

    user = User(
        username=username,
        email=email,
        password_hash=generate_password_hash(password)
    )
    
    # Assign default user role
    user_role = Role.query.filter_by(name='user').first()
    if user_role:
        user.roles.append(user_role)

    db.session.add(user)
    db.session.commit()

    return jsonify({"msg": "User created successfully", "user_id": user.id}), 201

@auth_bp.route('/login', methods=['POST'])
@limiter.limit("10 per minute")
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    user = User.query.filter_by(username=username).first()

    if not user or not check_password_hash(password, user.password_hash):
        return jsonify({"msg": "Invalid credentials"}), 401

    if not user.is_active:
        return jsonify({"msg": "Account is disabled"}), 403

    if user.mfa_enabled:
        # Require MFA verification
        temp_token = create_access_token(identity=user.id, additional_claims={"mfa_required": True}, expires_delta=datetime.timedelta(minutes=5))
        return jsonify({
            "msg": "MFA verification required",
            "mfa_required": True,
            "temp_token": temp_token
        }), 200

    # Normal Login
    access_token = create_access_token(identity=user.id)
    refresh_token = create_refresh_token(identity=user.id)
    
    # Decode refresh token to get JTI and Expiry
    decoded_refresh = decode_token(refresh_token)
    
    session = Session(
        user_id=user.id,
        refresh_token_jti=decoded_refresh['jti'],
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent', ''),
        expires_at=datetime.datetime.fromtimestamp(decoded_refresh['exp'], tz=timezone.utc)
    )
    db.session.add(session)
    db.session.commit()

    return jsonify({
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": {"id": user.id, "username": user.username, "roles": [r.name for r in user.roles]}
    }), 200

@auth_bp.route('/verify-mfa', methods=['POST'])
@jwt_required()
def verify_mfa():
    claims = get_jwt()
    if not claims.get("mfa_required"):
        return jsonify({"msg": "MFA not required for this token"}), 400

    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    data = request.get_json()
    token = data.get('token')
    
    if not token:
        return jsonify({"msg": "MFA token is required"}), 400
        
    if not verify_mfa_token(user.mfa_secret, token):
        return jsonify({"msg": "Invalid MFA token"}), 401

    # Issue full tokens
    access_token = create_access_token(identity=user.id)
    refresh_token = create_refresh_token(identity=user.id)
    
    decoded_refresh = decode_token(refresh_token)
    
    session = Session(
        user_id=user.id,
        refresh_token_jti=decoded_refresh['jti'],
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent', ''),
        expires_at=datetime.datetime.fromtimestamp(decoded_refresh['exp'], tz=timezone.utc)
    )
    db.session.add(session)
    db.session.commit()

    return jsonify({
        "access_token": access_token,
        "refresh_token": refresh_token
    }), 200

@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    current_user_id = get_jwt_identity()
    jti = get_jwt()['jti']
    
    session = Session.query.filter_by(refresh_token_jti=jti).first()
    
    if not session or session.is_revoked:
        return jsonify({"msg": "Invalid or revoked refresh token"}), 401
        
    if session.expires_at.replace(tzinfo=timezone.utc) < datetime.datetime.now(timezone.utc):
        return jsonify({"msg": "Refresh token expired"}), 401

    access_token = create_access_token(identity=current_user_id)
    return jsonify({"access_token": access_token}), 200

@auth_bp.route('/logout', methods=['POST'])
@jwt_required(refresh=True)
def logout():
    jti = get_jwt()['jti']
    session = Session.query.filter_by(refresh_token_jti=jti).first()
    if session:
        session.is_revoked = True
        db.session.commit()
    return jsonify({"msg": "Successfully logged out"}), 200
