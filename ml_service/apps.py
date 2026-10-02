from django.apps import AppConfig


class MlServiceConfig(AppConfig):
    name = 'ml_service'

    def ready(self):
        from . import signals  # noqa: F401
