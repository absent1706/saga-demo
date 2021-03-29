import logging
from celery import Celery

from consumer_service.app_common import settings
from consumer_service.app_common.messaging.consumer_service_messaging import \
    verify_consumer_details_message
from consumer_service.app_common.messaging import consumer_service_messaging, \
    CREATE_ORDER_SAGA_REPLY_QUEUE
from consumer_service.app_common.sagas_framework.utils import \
    success_task_name, failure_task_name

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

        payload = None  # nothing to return
        task_name = success_task_name(verify_consumer_details_message.TASK_NAME)
    except Exception as exc:
        logging.exception(exc)
        payload = serialize_saga_error(exc)
        task_name = failure_task_name(verify_consumer_details_message.TASK_NAME)

    send_saga_response(command_handlers_celery_app,
                       task_name,
                       CREATE_ORDER_SAGA_REPLY_QUEUE,
                       saga_id,
                       payload)



