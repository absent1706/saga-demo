from celery import Celery


def success_task_name(task_name: str):
    return f'{task_name}.response.success'


def failure_task_name(task_name: str):
    return f'{task_name}.response.failure'


def serialize_saga_error(exc: BaseException):
    import traceback

    exctype = type(exc)
    return {
        'type': getattr(exctype, '__qualname__', exctype.__name__),
        'message': str(exc),
        'module': exctype.__module__,
        'traceback': traceback.format_exc()
    }


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
