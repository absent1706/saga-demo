import logging
from dataclasses import dataclass, asdict

import typing
from celery import Celery, Task

from . import success_task_name, failure_task_name


logger = logging.getLogger(__name__)


@dataclass
class SagaErrorPayload:
    type: str
    message: str
    module: str
    traceback: str


def serialize_saga_error(exc: BaseException) -> SagaErrorPayload:
    import traceback

    exctype = type(exc)
    return SagaErrorPayload(
        type=getattr(exctype, '__qualname__', exctype.__name__),
        message=str(exc),
        module=exctype.__module__,
        traceback=traceback.format_exc()
    )


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


def saga_handler(response_queue: str):
    """
    Apply this decorator between @task and actual task handler.

    @command_handlers_celery_app.task(bind=True, name=verify_consumer_details_message.TASK_NAME)
    @saga_handler(CREATE_ORDER_SAGA_RESPONSE_QUEUE)

    Note: it's important to set bind=True in @task
      because @saga_handler will need access to celery task instance
    """
    def inner(func):
        def wrapper(celery_task: Task, saga_id: int, payload: dict):
            try:
                response_payload = func(celery_task, saga_id, payload)  # type: typing.Union[dict, None]
                # use convention response task name
                task_name = success_task_name(celery_task.name)
            except BaseException as exc:
                logger.exception(exc)
                # serialize error in a unified way
                response_payload = asdict(serialize_saga_error(exc))
                # use convention response task name
                task_name = failure_task_name(celery_task.name)

            send_saga_response(celery_task.app,
                               task_name,
                               response_queue,
                               saga_id,
                               response_payload)
        return wrapper

    return inner
