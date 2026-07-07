from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = 'api.core'

    def ready(self):
        import api.core.receivers
