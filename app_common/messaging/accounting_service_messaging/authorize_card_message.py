import dataclasses
from decimal import Decimal

import asyncapi


TASK_NAME = 'accounting_service.authorize_card'


@dataclasses.dataclass
class Payload:
    card_id: int
    amount: int


@dataclasses.dataclass
class Response:
    transaction_id: int


message = asyncapi.Message(
    name=TASK_NAME,
    title='Authorize previously saved card',
    summary='This command authorizes_money from previously saved card',
    payload=Payload,
)

response = asyncapi.Message(
    name=f'{TASK_NAME}.response',
    title='Transaction ID',
    payload=Response,
)
