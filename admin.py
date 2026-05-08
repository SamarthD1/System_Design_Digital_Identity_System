from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import User, Role, db
from functools import wraps

admin_bp = Blueprint('admin', __name__)

def admin_required():
    def wrapper(fn):
        @wraps(fn)
        @jwt_required()
        def decorator(*args, **kwargs):
            current_user_id = get_jwt_identity()
            user = User.query.get(current_user_id)
            if not user or not user.has_role('admin'):
                return jsonify({"msg": "Admin privileges required"}), 403
            return fn(*args, **kwargs)
        return decorator
    return wrapper

@admin_bp.route('/users', methods=['GET'])
@admin_required()
def get_users():
    users = User.query.all()
    result = []
    for user in users:
        result.append({
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "is_active": user.is_active,
            "roles": [r.name for r in user.roles]
        })
    return jsonify(result), 200

@admin_bp.route('/roles/assign', methods=['POST'])
@admin_required()
def assign_role():
    data = request.get_json()
    user_id = data.get('user_id')
    role_name = data.get('role_name')

    if not user_id or not role_name:
        return jsonify({"msg": "User ID and Role Name are required"}), 400

    user = User.query.get(user_id)
    if not user:
        return jsonify({"msg": "User not found"}), 404

    role = Role.query.filter_by(name=role_name).first()
    if not role:
        return jsonify({"msg": "Role not found"}), 404

    if not user.has_role(role_name):
        user.roles.append(role)
        db.session.commit()
        return jsonify({"msg": f"Role {role_name} assigned to user"}), 200
    else:
        return jsonify({"msg": "User already has this role"}), 400
