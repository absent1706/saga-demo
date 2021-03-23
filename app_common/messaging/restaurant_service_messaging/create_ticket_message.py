import dataclasses
from typing import List

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

response = asyncapi.Message(
    name=f'{TASK_NAME}.response',
    title='Response is just created restaurant ticket ID',
    payload=Response,
)
