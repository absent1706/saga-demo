from dataclasses import dataclass, asdict

from celery import Celery, Task


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
