"""
Authentication BluePrint για Bank api
Περιλαμβάνει routes Για register και Login
"""
from flask import Blueprint, request, jsonify, current_app
from app import db
from app.models import User
import jwt
from datetime import datetime, timedelta, timezone
import re

#Δημιουργία auth blueprint
auth_bp = Blueprint('auth',__name__, url_prefix='/api/auth')

def is_valid_email(email):
    """Έλεγχος αν το email είναι έγκυρο"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def is_strong_password(password:str):
    #second change
    if len(password) < 8:
        return False, "Password must be at least 8 charachters long"
    if not re.search(r'[A-Z]',password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    
    if not re.search(r'\d', password):
        return False, "Password must contain at least one number"
    
    return True, "Password is strong"

def exmaple_func(a:int, b:int,c:int) -> int:
    return a+b;

def generate_token(user_id):
    """Δημιουργία JWT token για τον user"""
    try:
        secret_key = current_app.config.get('SECRET_KEY')
        payload = {
            'user_id': user_id,
            'exp':  datetime.now(timezone.utc) + timedelta(hours=24),
            'iat':  datetime.now(timezone.utc)
        }
        token = jwt.encode(payload, secret_key, algorithm='HS256')
        return token
    except Exception as e:
        print(f"Token generation error: {str(e)}")
        current_app.logger.error(f"Token generation error: {str(e)}")
        return None

@auth_bp.route('/register',methods=['POST'])
def register():
    try:
        #λήψη δεδομένων από το request
        data = request.get_json()

        #ελέχνος αν υπάρχουν όλα τα απαιτούμενα πέδια
        required_fields = ['email','password','first_name','last_name']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'status':'fail',
                    'message': f'Missing required field {field}'
                }),400
            
        email = data['email'].lower().strip()
        password = data['password']
        first_name = data['first_name'].strip()
        last_name = data['last_name'].strip()
        phone = data.get('phone','').strip() if data.get('phone') else None

        #Validation Checks
        if not is_valid_email(email):
            return jsonify({
                'status' : 'error',
                'message': 'Invalid email format'
            }), 400
        
        is_strong, password_msg = is_strong_password(password)
        if not is_strong:
            return jsonify({
                'status':'error',
                'message':password_msg
            }), 400
        
        #Έλενχος αν το email υπάρχει ήδη
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return jsonify({
                'status':'error',
                'error': 'Email already registered'
            }), 409  # Conflict
        
        # Έλεγχος αν το phone υπάρχει ήδη (αν δόθηκε)
        if phone:
            existing_phone = User.query.filter_by(phone=phone).first()
            if existing_phone:
                return jsonify({
                    'status':'error',
                    'error': 'Phone number already registered'
                }), 409
        new_user = User(
            email = email,
            first_name = first_name,
            last_name = last_name,
            phone = phone
        )
        new_user.set_password(password)

        #Αποθυκευσή στην βάση
        db.session.add(new_user)
        db.session.commit()

        token = generate_token(new_user.id)
        return jsonify({
            'status':'Success',
            'message':'User registered successfully',
            'user': new_user.to_dict(),
            'token':token
        }),201

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Registration error: {str(e)}")
        return jsonify({
            'error':'Internal server error during registration'
        }), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        
        if not data.get('email') or not data.get('password'):
            return jsonify({
                'error': 'Email and password are required'
            }), 400
        
        email = data['email'].lower().strip()
        password = data['password']

        # Αναζήτηση user στη βάση
        user = User.query.filter_by(email=email).first()
        
        if not user or not user.check_password(password):
            return jsonify({
                'error': 'Invalid email or password'
            }), 401
        
        # Δημιουργία JWT token
        token = generate_token(user.id)
        
        if not token:
            return jsonify({
                'error': 'Could not generate authentication token'
            }), 500
        
        return jsonify({
            'message': 'Login successful',
            'user': user.to_dict(),
            'token': token
        }), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Login error: {str(e)}")
        return jsonify({
            'status':'error',
            'message':'Internal server error during login'
        }), 500
    
@auth_bp.route('/profile', methods=['GET'])
def get_profile():
    """
    Get User Profile (requires authentication)
    GET /api/auth/profile
    Headers: Authorization: Bearer <token>
    """
    try:
        # Αυτό θα το υλοποιήσουμε στο επόμενο βήμα με decorator
        return jsonify({
            'message': 'Profile endpoint - Authentication decorator needed'
        }), 501
        
    except Exception as e:
        current_app.logger.error(f"Profile error: {str(e)}")
        return jsonify({
            'error': 'Internal server error'
        }), 500