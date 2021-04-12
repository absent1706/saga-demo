import dataclasses
import asyncapi
from ...sagas_framework.asyncapi_utils import asyncapi_message_for_success_response

TASK_NAME = 'restaurant_service.reject_ticket'


@dataclasses.dataclass
class Payload:
    ticket_id: int


message = asyncapi.Message(
    name=TASK_NAME,
    title='Reject restaurant ticket',
    summary='This compensation command rejects already created restaurant ticket. \n'
            'Returns no response',
    payload=Payload,
)

success_response = asyncapi_message_for_success_response(TASK_NAME)
