import logging
import typing

from celery import Celery, Task
from saga_framework import saga_step_handler

from consumer_service.app_common import settings
from consumer_service.app_common.messaging import consumer_service_messaging, \
    CREATE_ORDER_SAGA_RESPONSE_QUEUE
from consumer_service.app_common.messaging.consumer_service_messaging import \
    verify_consumer_details_message

logging.basicConfig(level=logging.DEBUG)

command_handlers_celery_app = Celery(
    'consumer_command_handlers',
    broker=settings.CELERY_BROKER)
command_handlers_celery_app.conf.task_default_queue = consumer_service_messaging.COMMANDS_QUEUE


@command_handlers_celery_app.task(bind=True, name=verify_consumer_details_message.TASK_NAME)
@saga_step_handler(response_queue=CREATE_ORDER_SAGA_RESPONSE_QUEUE)
def verify_consumer_details_task(self: Task, saga_id: int, payload: dict) -> typing.Union[dict, None]:
    request_data = verify_consumer_details_message.Payload(**payload)

    # emulate an error if consumer_id is less than 50
    if request_data.consumer_id < 50:
        raise ValueError(f'Consumer has incorrect id = {request_data.consumer_id}')

    return None  # nothing to return



