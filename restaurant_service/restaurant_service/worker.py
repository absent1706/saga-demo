import logging
import random
from dataclasses import asdict

from celery import Celery

from restaurant_service.app_common import settings
from restaurant_service.app_common.messaging import restaurant_service_messaging, \
    CREATE_ORDER_SAGA_REPLY_QUEUE
from restaurant_service.app_common.messaging.restaurant_service_messaging import \
    create_ticket_message, reject_ticket_message, approve_ticket_message
from restaurant_service.app_common.sagas_framework import success_task_name, \
    failure_task_name, serialize_saga_error, send_saga_response

logging.basicConfig(level=logging.DEBUG)

command_handlers_celery_app = Celery(
    'restaurant_command_handlers',
    broker=settings.CELERY_BROKER,
    backend=settings.CELERY_RESULT_BACKEND)
command_handlers_celery_app.conf.task_default_queue = restaurant_service_messaging.COMMANDS_QUEUE


@command_handlers_celery_app.task(name=create_ticket_message.TASK_NAME)
def create_ticket_task(saga_id: int, payload: dict):
    try:
        payload = create_ticket_message.Payload(**payload)

        # in real world, we would create a ticket in restaurant service DB
        # here, we will just generate some fake ID of just created ticket
        ticket_id = random.randint(200, 300)
        logging.info(f'Restaurant ticket {ticket_id} created')

        payload = asdict(create_ticket_message.Response(
            ticket_id=ticket_id
        ))
        task_name = success_task_name(create_ticket_message.TASK_NAME)
    except Exception as exc:
        logging.exception(exc)
        payload = serialize_saga_error(exc)
        task_name = failure_task_name(create_ticket_message.TASK_NAME)

    send_saga_response(command_handlers_celery_app,
                       task_name,
                       CREATE_ORDER_SAGA_REPLY_QUEUE,
                       saga_id,
                       payload)


@command_handlers_celery_app.task(name=reject_ticket_message.TASK_NAME)
def reject_ticket_task(saga_id: int, payload: dict):
    try:
        payload = reject_ticket_message.Payload(**payload)

        # in real world, we would reject a ticket in restaurant service DB
        logging.info(f'Restaurant ticket {payload.ticket_id} rejected')

        payload = None
        task_name = success_task_name(reject_ticket_message.TASK_NAME)
    except Exception as exc:
        logging.exception(exc)
        payload = serialize_saga_error(exc)
        task_name = failure_task_name(reject_ticket_message.TASK_NAME)

    send_saga_response(command_handlers_celery_app,
                       task_name,
                       CREATE_ORDER_SAGA_REPLY_QUEUE,
                       saga_id,
                       payload)

    return None


@command_handlers_celery_app.task(name=approve_ticket_message.TASK_NAME)
def approve_ticket_task(payload: dict):
    payload = approve_ticket_message.Payload(**payload)

    # in real world, we would change ticket status to 'approved' in service DB
    logging.info(f'Restaurant ticket {payload.ticket_id} approved')

    return None
