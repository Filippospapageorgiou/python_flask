from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from app.config import config
import os

db = SQLAlchemy()
migrate = Migrate()

def create_app(config_name=None):
    app = Flask(__name__)

    #2φορτωνούμε τα config
    config_name = config_name or os.environ.get('FLASK_ENV', 'default')
    config_obj = config[config_name]
    app.config.from_object(config_obj)
    
    #3.Αρχικοποιύμε τα extensions με το app
    db.init_app(app)
    # ΔΙΟΡΘΩΣΗ: Πρέπει να περάσουμε το db object στο migrate
    migrate.init_app(app, db)

    #4.εισάγουμε τα models
    from app import models

    #5.καταχωρούμε τα routes/blueprints
    #blueprints  τρόπος να οργανώσουμε τα routes σε groupes
    from app.routes import main_bp
    app.register_blueprint(main_bp)

    #6 Error handlers - gloabal exception handling
    @app.errorhandler(404)
    def not_found(error):
        return {'error':'Resource not found'}, 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return {'error':'Internal server error'}, 500
    
    @app.route('/health')  # ΔΙΟΡΘΩΣΗ: typo στο '/healte'
    def health_check():
        return {
            'status':'healthy',
            'service':'bank-api',
            'environment':config_name
        }, 200
    
    return app