from dataclasses import dataclass

from celery import Celery


def success_task_name(task_name: str):
    return f'{task_name}.response.success'


def failure_task_name(task_name: str):
    return f'{task_name}.response.failure'


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
