import dataclasses
import asyncapi


TASK_NAME = 'restaurant_service.approve_ticket'


@dataclasses.dataclass
class Payload:
    ticket_id: int


message = asyncapi.Message(
    name=TASK_NAME,
    title='Approve restaurant ticket',
    summary='This command approves previously created restaurant ticket. \n'
            'Returns no response',
    payload=Payload,
)
