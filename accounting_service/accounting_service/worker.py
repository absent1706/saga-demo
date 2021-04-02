import logging
import random
from dataclasses import asdict

from celery import Celery

from accounting_service.app_common import settings
from accounting_service.app_common.messaging import \
    accounting_service_messaging, CREATE_ORDER_SAGA_REPLY_QUEUE
from accounting_service.app_common.messaging.accounting_service_messaging import \
    authorize_card_message
from accounting_service.app_common.sagas_framework import success_task_name, \
    serialize_saga_error, failure_task_name, send_saga_response

logging.basicConfig(level=logging.DEBUG)

command_handlers_celery_app = Celery(
    'accounting_command_handlers',
    broker=settings.CELERY_BROKER,
    backend=settings.CELERY_RESULT_BACKEND)
command_handlers_celery_app.conf.task_default_queue = accounting_service_messaging.COMMANDS_QUEUE


@command_handlers_celery_app.task(name=authorize_card_message.TASK_NAME)
def authorize_card_task(saga_id: int, payload: dict):
    try:
        payload = authorize_card_message.Payload(**payload)

        # emulate an error
        if payload.amount >= 50:
            raise ValueError('Card authorization failed. Insiffucient balance')

        # in real app, we would create here DB record with order ID and transaction ID
        transaction_id = random.randint(100, 1000)
        payload = asdict(authorize_card_message.Response(transaction_id=transaction_id))

        task_name = success_task_name(authorize_card_message.TASK_NAME)
    except Exception as exc:
        logging.exception(exc)
        payload = asdict(serialize_saga_error(exc))
        task_name = failure_task_name(authorize_card_message.TASK_NAME)

    send_saga_response(command_handlers_celery_app,
                       task_name,
                       CREATE_ORDER_SAGA_REPLY_QUEUE,
                       saga_id,
                       payload)
