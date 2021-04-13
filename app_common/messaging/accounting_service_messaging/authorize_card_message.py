import dataclasses

import asyncapi

from accounting_service.app_common.sagas_framework.asyncapi_utils import \
    asyncapi_message_for_success_response

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

success_response = asyncapi_message_for_success_response(
    TASK_NAME,
    title='Transaction ID is returned',
    payload_dataclass=Response
)

