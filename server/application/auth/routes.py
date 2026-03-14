# app/auth/routes.py
# Contains routes related to authentication, like login.
from flask import request, jsonify
from . import auth_bp
from ..models import User, TokenBlocklist
from ..extensions import bcrypt, db
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity, get_jwt
import logging

logger = logging.getLogger(__name__)

@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Logs in a user (admin or client) and returns JWT access and refresh tokens.
    Identity in JWT will be the user's ID as a string.
    """
    data = request.get_json()
    logger.info(f"Login request received, data: {data}")
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({"msg": "Missing username or password"}), 400

    username = data['username']
    password = data['password']

    try:
        logger.info(f"Querying user: {username}")
        user = User.query.filter_by(username=username).first()
        logger.info(f"User query result: {user}")

        if user:
            logger.info("Checking password...")
            is_valid = user.check_password(password)
            logger.info(f"Password check result: {is_valid}")
            
            if is_valid:
                # Store user's ID as a string in the JWT identity
                string_identity = str(user.id)
                access_token = create_access_token(identity=string_identity)
                refresh_token = create_refresh_token(identity=string_identity)
                logger.info("Login successful. Returning tokens.")
                return jsonify(access_token=access_token, refresh_token=refresh_token), 200
        
        logger.info("Login failed: Bad username or password")
        return jsonify({"msg": "Bad username or password"}), 401
    except Exception as e:
        logger.error(f"Error during login: {e}", exc_info=True)
        return jsonify({"msg": "Internal server error"}), 500

@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True) # Requires a valid refresh token
def refresh():
    """
    Provides a new access token using a refresh token.
    The identity from the refresh token (user ID string) is used for the new access token.
    """
    try:
        logger.info("Token refresh endpoint called")
        current_user_identity_str = get_jwt_identity() # This will be the user ID string
        logger.info(f"Refreshing token for user ID: {current_user_identity_str}")
        new_access_token = create_access_token(identity=current_user_identity_str)
        return jsonify(access_token=new_access_token), 200
    except Exception as e:
        logger.error(f"Error refreshing token: {e}", exc_info=True)
        return jsonify({"msg": "Internal server error"}), 500

@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """
    Logs out a user and adds their token to the blocklist.
    """
    try:
        logger.info("Logout endpoint called")
        jti = get_jwt()['jti']
        logger.info(f"Adding token {jti} to blocklist")
        db.session.add(TokenBlocklist(jti=jti))
        db.session.commit()
        logger.info("Token added to blocklist successfully")
        return jsonify({"msg": "Logout successful."}), 200
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error during logout: {e}", exc_info=True)
        return jsonify({"msg": "Internal server error"}), 500
