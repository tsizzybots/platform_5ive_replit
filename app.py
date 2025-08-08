import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Enable CORS for API access
CORS(app)

# Configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "postgresql://localhost/helpdesk")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize the app with the extension
db.init_app(app)

def initialize_app():
    """Initialize the application with proper error handling"""
    try:
        with app.app_context():
            # Import models to ensure tables are created
            import models  # noqa: F401
            
            # Test database connection first
            try:
                from sqlalchemy import text
                db.session.execute(text('SELECT 1'))
                logging.info("Database connection successful")
            except Exception as db_error:
                logging.error(f"Database connection failed: {str(db_error)}")
                # Still try to create tables in case it's a permission issue
                
            # Create all tables
            try:
                db.create_all()
                logging.info("Database tables created successfully")
            except Exception as table_error:
                logging.error(f"Failed to create database tables: {str(table_error)}")
                raise
                
    except Exception as e:
        logging.error(f"Application initialization failed: {str(e)}")
        raise

# Import routes at module level
try:
    from routes import *  # noqa: F401, F403
    logging.info("Routes imported successfully")
except Exception as route_error:
    logging.error(f"Failed to import routes: {str(route_error)}")

# Initialize the application
try:
    initialize_app()
    logging.info("Application initialized successfully")
except Exception as init_error:
    logging.error(f"Critical error during initialization: {str(init_error)}")
    # Don't raise here - let the app start even with some issues

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
