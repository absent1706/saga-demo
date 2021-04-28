import logging
import random
from dataclasses import asdict

from celery import Celery, Task
from saga_framework import saga_step_handler

from accounting_service.app_common import settings
from accounting_service.app_common.messaging import \
    accounting_service_messaging, CREATE_ORDER_SAGA_RESPONSE_QUEUE
from accounting_service.app_common.messaging.accounting_service_messaging import \
    authorize_card_message

logging.basicConfig(level=logging.DEBUG)

command_handlers_celery_app = Celery(
    'accounting_command_handlers',
    broker=settings.CELERY_BROKER)
command_handlers_celery_app.conf.task_default_queue = accounting_service_messaging.COMMANDS_QUEUE


@command_handlers_celery_app.task(bind=True, name=authorize_card_message.TASK_NAME)
@saga_step_handler(response_queue=CREATE_ORDER_SAGA_RESPONSE_QUEUE)
def authorize_card_task(self: Task, saga_id: int, payload: dict) -> dict:
    request_data = authorize_card_message.Payload(**payload)

    # emulate an error
    if request_data.amount >= 50:
        raise ValueError('Card authorization failed. Insiffucient balance')

    # in real app, we would create here DB record with order ID and transaction ID
    transaction_id = random.randint(100, 1000)
    return asdict(authorize_card_message.Response(
        transaction_id=transaction_id
    ))
