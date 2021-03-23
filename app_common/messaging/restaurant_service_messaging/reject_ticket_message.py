import dataclasses
import asyncapi


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
