#!/usr/bin/env python3
"""
Entry point για την Bank api εφαρμογή
Αυτό το αρχείο:
1. Δημιουργεί το Flask app χρησιμοποιώντας το Application Factory
2.Τρέχει την εφαρμογή όταν εκτελείται directly(python run.py)
"""
import os
from app import create_app
from dotenv import load_dotenv

# Debug: Φόρτωσε το .env file explicitly
load_dotenv()

# Debug: Έλεγχος environment variables
print(f"🔍 DATABASE_URL found: {bool(os.environ.get('DATABASE_URL'))}")
print(f"🔍 SECRET_KEY found: {bool(os.environ.get('SECRET_KEY'))}")


#δημιουργούμε το app instance χρησιμοποιώντας το factory pattern
app = create_app()

# Αυτό τρέχει ΜΟΝΟ όταν εκτελούμε το αρχείο directly
# python run.py
if __name__ == '__main__':
    """
    Development server - ΜΗ χρησιμοποιείς για production!
    
    Για production θα χρησιμοποιήσεις:
    - gunicorn run:app
    - uwsgi
    - deployment σε cloud (Heroku, AWS, etc.)
    """
    host = os.environ.get('FLASK_HOST','127.0.0.1')
    port = int(os.environ.get('FLASK_PORT',5000))
    debug = os.environ.get('DEBUG','True').lower() == 'true'

    print(f"🚀 Starting Bank API on {host}:{port}")
    print(f"🔧 Debug mode: {debug}")
    print(f"🌍 Environment: {os.environ.get('FLASK_ENV', 'development')}")
    
    # Εκκίνηση του development server
    app.run(
        host=host,      # 127.0.0.1 = localhost only, 0.0.0.0 = όλα τα interfaces
        port=port,      # Port number
        debug=debug,    # Auto-reload on code changes + debug info
        threaded=True   # Handle multiple requests simultaneously
    )

