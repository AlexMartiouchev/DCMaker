from django.apps import AppConfig


class PopulatorConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "populator"

    def ready(self):
        # Wire the engine's metering hooks to the Django-side ledger.
        # Imported here rather than at module level because usage.py
        # touches models, which are not loaded until apps are ready.
        from .generation import client
        from . import usage

        client.set_hooks(before=usage.before_call, after=usage.record)
