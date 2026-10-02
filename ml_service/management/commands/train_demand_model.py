from django.core.management.base import BaseCommand

from ml import demand_forecast
from ml_service.ai_restock_service import invalidate_restock_cache


class Command(BaseCommand):
    help = "Train the area demand model and save it for the web app to load."

    def add_arguments(self, parser):
        parser.add_argument(
            "--plot", metavar="PATH",
            help="Also save a chart of the fit and forecast to this PNG file.",
        )

    def handle(self, *args, **options):
        artifact = demand_forecast.train_and_save(plot_path=options["plot"])
        invalidate_restock_cache()

        total, _ = demand_forecast.predict_next_week_demand()
        self.stdout.write(self.style.SUCCESS(
            f"Saved model to {demand_forecast.MODEL_PATH} "
            f"(trained through day {artifact['last_day']}, next week total: {total})"
        ))
