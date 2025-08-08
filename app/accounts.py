from flask import Blueprint, request, jsonify, current_app, g
from app import db
from app.models import User, Account, Transaction
from app.decorators import token_required
import jwt
from datetime import datetime, timedelta, timezone
import re

accounts_bp =  Blueprint('accounts',__name__, url_prefix='/accounts')

@accounts_bp.route('/',methods = ['GET'])
@token_required
def get_accounts_info():
    try:
        user = g.current_user

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Registration error: {str(e)}")
        return jsonify({
            'error':'Internal server error during registration'
        }), 500
