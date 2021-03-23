import logging
import random
from dataclasses import asdict

from celery import Celery

from restaurant_service.app_common import settings
from restaurant_service.app_common.messaging import restaurant_service_messaging
from restaurant_service.app_common.messaging.restaurant_service_messaging import \
    create_ticket_message, reject_ticket_message, approve_ticket_message

logging.basicConfig(level=logging.DEBUG)

command_handlers_celery_app = Celery(
    'restaurant_command_handlers',
    broker=settings.CELERY_BROKER,
    backend=settings.CELERY_RESULT_BACKEND)
command_handlers_celery_app.conf.task_default_queue = restaurant_service_messaging.COMMANDS_QUEUE


@command_handlers_celery_app.task(name=create_ticket_message.TASK_NAME)
def create_ticket_task(payload: dict):
    payload = create_ticket_message.Payload(**payload)

    # in real world, we would create a ticket in restaurant service DB
    # here, we will just generate some fake ID of just created ticket
    ticket_id = random.randint(200, 300)
    logging.info(f'Restaurant ticket {ticket_id} created')

    return asdict(create_ticket_message.Response(ticket_id=ticket_id))


@command_handlers_celery_app.task(name=reject_ticket_message.TASK_NAME)
def reject_ticket_task(payload: dict):
    payload = reject_ticket_message.Payload(**payload)

    # in real world, we would reject a ticket in restaurant service DB
    logging.info(f'Restaurant ticket {payload.ticket_id} rejected')

    return None


@command_handlers_celery_app.task(name=approve_ticket_message.TASK_NAME)
def approve_ticket_task(payload: dict):
    payload = approve_ticket_message.Payload(**payload)

    # in real world, we would change ticket status to 'approved' in service DB
    logging.info(f'Restaurant ticket {payload.ticket_id} approved')

    return None
