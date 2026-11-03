import os
from flask import Flask
from app.config import Config
from app.db import init_app


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Ensure upload directory exists
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    
    # Register DB hooks and migrations
    init_app(app)
    
    # Register Blueprints
    from app.blueprints.main import main_bp
    from app.blueprints.tv import tv_bp
    from app.blueprints.admin import admin_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(tv_bp)
    app.register_blueprint(admin_bp)
    
    return app
