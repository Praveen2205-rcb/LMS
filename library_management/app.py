from __future__ import annotations
import os
from flask import Flask
from dotenv import load_dotenv

load_dotenv()

def create_app() -> Flask:
    app = Flask(__name__,
                template_folder="frontend/templates",
                static_folder="frontend/static")
    app.secret_key = os.getenv("SECRET_KEY", "change-me-in-production")
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024

    from backend.database import init_db
    with app.app_context():
        init_db()

    from backend.routes.auth import auth_bp
    from backend.routes.admin import admin_bp
    from backend.routes.librarian import librarian_bp
    from backend.routes.member import member_bp
    from backend.routes.api import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(librarian_bp)
    app.register_blueprint(member_bp)
    app.register_blueprint(api_bp)

    return app


if __name__ == "__main__":
    from backend.utils.backup import start_scheduler
    start_scheduler()
    app = create_app()
    app.run(debug=True, host="0.0.0.0", port=5000, use_reloader=False)
