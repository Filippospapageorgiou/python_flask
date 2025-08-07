import os
from dotenv import load_dotenv

# Φορτώνουμε τις environment variables από το .env αρχείο
load_dotenv()

class Config:
    """
    Βασική κλάση configuration - κοινές ρυθμίσεις για όλα τα environments
    Παρόμοια με application.properties στο Spring Boot
    """
    
    # Secret key για sessions και JWT tokens
    # Σαν το spring.application.secret
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'fallback-secret-key'
    
    # Database connection string
    # Σαν το spring.datasource.url
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    
    # Debug: Εκτυπώνουμε την τιμή για debugging
    print(f"🔧 Config: DATABASE_URL = {SQLALCHEMY_DATABASE_URI}")
    
    if not SQLALCHEMY_DATABASE_URI:
        print("⚠️  WARNING: DATABASE_URL not found in environment variables!")
        print("📄 Make sure you have a .env file with DATABASE_URL")
        # Fallback για development
        SQLALCHEMY_DATABASE_URI = 'sqlite:///fallback_bank.db'
        print(f"🔧 Using fallback SQLite: {SQLALCHEMY_DATABASE_URI}")
    
    # Απενεργοποιεί το SQLAlchemy event system (performance optimization)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # JWT settings
    JWT_SECRET_KEY = os.environ.get('SECRET_KEY') or SECRET_KEY
    JWT_ACCESS_TOKEN_EXPIRES = 3600  # 1 ώρα σε seconds

class DevelopmentConfig(Config):
    """
    Configuration για development
    Παρόμοια με application-dev.properties
    """
    DEBUG = True
    # Εκτυπώνει τα SQL queries στο console (για debugging)
    SQLALCHEMY_ECHO = True

class ProductionConfig(Config):
    """
    Configuration για production
    Παρόμοια με application-prod.properties
    """
    DEBUG = False
    SQLALCHEMY_ECHO = False

class TestingConfig(Config):
    """Configuration για unit tests"""
    TESTING = True
    # Χρησιμοποιούμε in-memory SQLite για tests
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

# Dictionary για εύκολη επιλογή configuration
# Στο Spring Boot αυτό γίνεται με profiles
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}