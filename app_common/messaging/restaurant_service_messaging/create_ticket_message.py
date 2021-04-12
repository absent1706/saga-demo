import dataclasses
from typing import List
from ...sagas_framework.asyncapi_utils import asyncapi_message_for_success_response, \
    asyncapi_message_for_failure_response

import asyncapi


TASK_NAME = 'restaurant_service.create_ticket'


@dataclasses.dataclass
class OrderItem:
    name: str
    quantity: int


@dataclasses.dataclass
class Payload:
    order_id: int
    customer_id: int
    items: List[OrderItem]


@dataclasses.dataclass
class Response:
    ticket_id: int


message = asyncapi.Message(
    name=TASK_NAME,
    title='Create restaurant ticket',
    summary='This command creates ticket so restaurant knows order details. \n'
            'In real world, ticket may be created automatically or after restaurant manager approves it '
            '(confirm that they will be able to cook desired dishes)',
    payload=Payload,
)

success_response = asyncapi_message_for_success_response(
    TASK_NAME,
    title='Ticket ID is returned',
    payload_dataclass=Response
)

# failure_response = asyncapi_message_for_failure_response(TASK_NAME)
