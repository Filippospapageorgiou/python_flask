"""
Authentication Decorators για Bank API
Περιλαμβάνει JWT token validation
"""
from functools import wraps
from flask import request, jsonify, current_app, g
import jwt
from app.models import User

def token_required(f):
    """
    Decorator που ελέγχει αν υπάρχει έγκυρο JWT token
    Χρήση: @token_required πάνω από την route function
    
    Το token περνάει στο Authorization header ως:
    Authorization: Bearer <token>
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Έλεγχος αν υπάρχει Authorization header
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                # Format: "Bearer <token>"
                token = auth_header.split(" ")[1]
            except IndexError:
                return jsonify({
                    'error': 'Invalid authorization header format. Use: Bearer <token>'
                }), 401
        
        if not token:
            return jsonify({
                'error': 'Access token is missing'
            }), 401
        
        try:
            # Decode και validate το JWT token
            data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
            current_user_id = data['user_id']
            
            # Βρες τον user στη βάση
            current_user = User.query.get(current_user_id)
            if not current_user:
                return jsonify({
                    'error': 'User not found'
                }), 401
            
            # Αποθήκευσε τον current user στο Flask g object
            # Έτσι μπορούμε να τον χρησιμοποιήσουμε σε οποιαδήποτε protected route
            g.current_user = current_user
            
        except jwt.ExpiredSignatureError:
            return jsonify({
                'error': 'Token has expired'
            }), 401
        except jwt.InvalidTokenError:
            return jsonify({
                'error': 'Token is invalid'
            }), 401
        except Exception as e:
            current_app.logger.error(f"Token validation error: {str(e)}")
            return jsonify({
                'error': 'Token validation failed'
            }), 401
        
        # Αν όλα πάνε καλά, κάλεσε την αρχική function
        return f(*args, **kwargs)
    
    return decorated

def admin_required(f):
    """
    Decorator που ελέγχει αν ο user είναι admin
    Προϋποθέτει ότι έχει τρέξει πρώτα @token_required
    
    Σημείωση: Δεν έχουμε ακόμα admin field στο User model
    Αυτό είναι placeholder για μελλοντική χρήση
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if not hasattr(g, 'current_user'):
            return jsonify({
                'error': 'Authentication required'
            }), 401
            
        # Προς το παρόν, μόνο user με id=1 είναι admin (temporary)
        if g.current_user.id != 1:
            return jsonify({
                'error': 'Admin access required'
            }), 403
        
        return f(*args, **kwargs)
    
    return decorated