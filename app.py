from flask import Flask
from config import Config
from extensions import db


def create_app():
    app = Flask(__name__, template_folder="web/templates", static_folder="web/static")
    app.config.from_object(Config)

    db.init_app(app)

    from routes.api import api_bp
    from routes.views import views_bp
    app.register_blueprint(api_bp)
    app.register_blueprint(views_bp)

    with app.app_context():
        db.create_all()
        _initial_load(app)

    from services.scheduler_service import start_scheduler
    start_scheduler(app)

    return app


def _initial_load(app):
    from models import Game
    if Game.query.count() == 0:
        from services.odds_service import OddsService
        from services.projection_service import ProjectionService
        OddsService().fetch_and_store()
        ProjectionService().calculate_all()
        app.logger.info("Carga inicial concluída")


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=5001, use_reloader=False)
