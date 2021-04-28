import logging
import random
import typing
from dataclasses import asdict

from celery import Celery, Task
from saga_framework import saga_step_handler, no_response_saga_step_handler
from saga_framework.celery_utils import auto_retry_then_reraise

from restaurant_service.app_common import settings
from restaurant_service.app_common.messaging import \
    restaurant_service_messaging, \
    CREATE_ORDER_SAGA_RESPONSE_QUEUE
from restaurant_service.app_common.messaging.restaurant_service_messaging import \
    create_ticket_message, reject_ticket_message, approve_ticket_message

logging.basicConfig(level=logging.DEBUG)

command_handlers_celery_app = Celery(
    'restaurant_command_handlers',
    broker=settings.CELERY_BROKER)
command_handlers_celery_app.conf.task_default_queue = restaurant_service_messaging.COMMANDS_QUEUE


@command_handlers_celery_app.task(bind=True, name=create_ticket_message.TASK_NAME)
@saga_step_handler(response_queue=CREATE_ORDER_SAGA_RESPONSE_QUEUE)
def create_ticket_task(self: Task, saga_id: int, payload: dict) -> dict:
    request_data = create_ticket_message.Payload(**payload)

    # in real world, we would create a ticket in restaurant service DB
    # here, we will just generate some fake ID of just created ticket
    ticket_id = random.randint(200, 300)
    logging.info(f'Restaurant ticket {request_data} created')
    logging.info(f'Ticket details: {payload}')

    return asdict(create_ticket_message.Response(
        ticket_id=ticket_id
    ))


@command_handlers_celery_app.task(bind=True, name=reject_ticket_message.TASK_NAME)
@no_response_saga_step_handler  # no response is sent back to orchestrator. it's typical for compensation steps
def reject_ticket_task(self: Task, saga_id: int, payload: dict) -> typing.Union[dict, None]:
    request_data = reject_ticket_message.Payload(**payload)

    # in real world, we would reject a ticket in restaurant service DB
    logging.info(f'Restaurant ticket {request_data.ticket_id} rejected')

    return None


@command_handlers_celery_app.task(
    bind=True, name=approve_ticket_message.TASK_NAME,
    default_retry_delay=5  # set some small retry delay to not wait 3 minutes Celery sets by default
)
@saga_step_handler(response_queue=CREATE_ORDER_SAGA_RESPONSE_QUEUE)
@auto_retry_then_reraise(max_retries=2)  # retry task 2 times, then re-raise exception
def approve_ticket_task(self: Task, saga_id: int, payload: dict) -> typing.Union[dict, None]:
    request_data = approve_ticket_message.Payload(**payload)

    # emulate 50%-probable first-time failure
    if random.random() < 0.3:
        raise EnvironmentError('test error message. Task will retry now')

    # in real world, we would change ticket status to 'approved' in service DB
    logging.info(f'Restaurant ticket {request_data.ticket_id} approved')

    return None
