from celery import Celery

from app.infrastructure.config import get_settings

settings = get_settings()

celery_app = Celery("demo",
                    broker=settings.broker_url,
                    backend=settings.result_backend)
