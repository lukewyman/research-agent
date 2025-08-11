import os
from celery import Celery

BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
RESULT_URL = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")

app = Celery("research", broker=BROKER_URL, backend=RESULT_URL)
app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    result_expires=86400,  # 1 day
    worker_send_task_events=True,
)
