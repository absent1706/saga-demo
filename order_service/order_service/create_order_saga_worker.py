import logging

from app_common.sagas_framework import \
    close_sqlalchemy_db_connection_after_celery_task_ends

logging.basicConfig(level=logging.DEBUG)

from celery import Celery

from order_service.app_common import settings
from order_service.app_common.messaging import CREATE_ORDER_SAGA_RESPONSE_QUEUE

from .app import CreateOrderSaga, db

create_order_saga_responses_celery_app = Celery(
    'create_order_saga_responses',
    broker=settings.CELERY_BROKER)
create_order_saga_responses_celery_app.conf.task_default_queue = CREATE_ORDER_SAGA_RESPONSE_QUEUE

close_sqlalchemy_db_connection_after_celery_task_ends(db.session)

CreateOrderSaga.register_async_step_handlers(create_order_saga_responses_celery_app)
