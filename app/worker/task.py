from app.worker.celery import celery_app


@celery_app.task
def process_order(order_id: int) -> None:
    pass