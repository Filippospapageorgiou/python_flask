
from flask import Blueprint, jsonify

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def home():
    return {
        'message' : 'Welcome to bank API',
        'version' : '1.0',
        'endpoints' : {
            'health' : '/health',
            'docs'  : 'Coming soon...'
        }
    }

@main_bp.route('/api')
def api_info():
    return {
        'api': 'Bank API',
        'version': '1.0',
        'status': 'Development',
        'available_endpoints': [
            'POST /api/auth/register',
            'POST /api/auth/login', 
            'GET /api/accounts',
            'POST /api/accounts/deposit',
            'POST /api/accounts/withdraw',
            'POST /api/accounts/transfer'
        ]
    }