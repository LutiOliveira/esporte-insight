from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger


def start_scheduler(app):
    scheduler = BackgroundScheduler()

    def refresh():
        with app.app_context():
            from services.odds_service import OddsService
            from services.projection_service import ProjectionService
            OddsService().fetch_and_store()
            ProjectionService().calculate_all()
            app.logger.info("Dados atualizados pelo scheduler")

    scheduler.add_job(
        func=refresh,
        trigger=IntervalTrigger(hours=1),
        id="refresh_data",
        replace_existing=True,
    )
    scheduler.start()
    return scheduler
