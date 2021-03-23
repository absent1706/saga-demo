import dataclasses

import asyncapi


TASK_NAME = 'consumer_service.verify_consumer_details'
RESPONSE_TASK_NAME = f'{TASK_NAME}.response'


@dataclasses.dataclass
class Payload:
    consumer_id: int


message = asyncapi.Message(
    name=TASK_NAME,
    title='Verify consumer details',
    summary='This command makes consumer service verify consumer details.'
            'If consumer is correct, it returns nothing.'
            'If validation fails, it throws an exception',
    payload=Payload,
)
