import logging
import random
import time
from dataclasses import asdict

from celery import Celery
import celery

from consumer_service.app_common import settings
from consumer_service.app_common.messaging.consumer_service_messaging import \
    verify_consumer_details_message
from consumer_service.app_common.messaging import consumer_service_messaging, \
    CREATE_ORDER_SAGA_REPLY_QUEUE
from consumer_service.app_common.messaging.utils import \
    success_response_task_name, failure_response_task_name

logging.basicConfig(level=logging.DEBUG)

command_handlers_celery_app = Celery(
    'consumer_command_handlers',
    broker=settings.CELERY_BROKER)
command_handlers_celery_app.conf.task_default_queue = consumer_service_messaging.COMMANDS_QUEUE


def send_saga_response(celery_app: Celery,
                       response_task_name: str,
                       response_queue_name: str,
                       saga_id: int,
                       payload):  # assuming payload is a @dataclass
    return celery_app.send_task(
        response_task_name,
        args=[
            saga_id,
            payload
        ],
        queue=response_queue_name
    )


def serialize_saga_error(exc: BaseException):
    import traceback

    exctype = type(exc)
    return {
        'type': getattr(exctype, '__qualname__', exctype.__name__),
        'message': str(exc),
        'module': exctype.__module__,
        'traceback': traceback.format_exc()
    }


@command_handlers_celery_app.task(name=verify_consumer_details_message.TASK_NAME,
                                  reply_queue=CREATE_ORDER_SAGA_REPLY_QUEUE)
def verify_consumer_details_task(saga_id: int, payload: dict):
    try:
        payload = verify_consumer_details_message.Payload(**payload)

        # emulate an error if consumer_id is less than 50
        if payload.consumer_id < 50:
            raise ValueError(f'Consumer has incorrect id = {payload.consumer_id}')

        payload = None

        send_saga_response(command_handlers_celery_app,
                           success_response_task_name(verify_consumer_details_message.TASK_NAME),
                           CREATE_ORDER_SAGA_REPLY_QUEUE,
                           saga_id,
                           payload)
    except Exception as exc:
        logging.exception(exc)

        send_saga_response(command_handlers_celery_app,
                           failure_response_task_name(verify_consumer_details_message.TASK_NAME),
                           CREATE_ORDER_SAGA_REPLY_QUEUE,
                           saga_id,
                           payload=serialize_saga_error(exc))

    # TODO: maybe: for failures, use another task name => status not needed



