import logging
import random
from dataclasses import asdict

from celery import Celery

from accounting_service.app_common import settings
from accounting_service.app_common.messaging import accounting_service_messaging
from accounting_service.app_common.messaging.accounting_service_messaging import \
    authorize_card_message

logging.basicConfig(level=logging.DEBUG)

command_handlers_celery_app = Celery(
    'accounting_command_handlers',
    broker=settings.CELERY_BROKER,
    backend=settings.CELERY_RESULT_BACKEND)
command_handlers_celery_app.conf.task_default_queue = accounting_service_messaging.COMMANDS_QUEUE


@command_handlers_celery_app.task(name=authorize_card_message.TASK_NAME)
def authorize_card_task(payload: dict):
    payload = authorize_card_message.Payload(**payload)

    # emulate an error
    if payload.amount >= 50:
        raise ValueError('Card authorization failed. Insiffucient balance')

    # in real app, we would create here DB record with order ID and transaction ID

    transaction_id = random.randint(100, 1000)
    return asdict(authorize_card_message.Response(transaction_id=transaction_id))
