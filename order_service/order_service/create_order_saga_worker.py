from celery import Celery

from order_service.app_common import settings
from order_service.app_common.messaging import CREATE_ORDER_SAGA_RESPONSE_QUEUE

from order_service.app import CreateOrderSaga

create_order_saga_responses_celery_app = Celery(
    'create_order_saga_responses',
    broker=settings.CELERY_BROKER)
create_order_saga_responses_celery_app.conf.task_default_queue = CREATE_ORDER_SAGA_RESPONSE_QUEUE

CreateOrderSaga.register_async_step_handlers(create_order_saga_responses_celery_app)
