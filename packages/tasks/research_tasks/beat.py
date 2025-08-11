from .celery_app import app

# No static schedule here; pass -s / use CLI or celery beat --schedule file.db
# You can also configure app.conf.beat_schedule from env in celery_app.py if desired.
