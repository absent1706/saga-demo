import dataclasses

import asyncapi

from consumer_service.app_common.sagas_framework.asyncapi_utils import \
    asyncapi_message_for_success_response

TASK_NAME = 'consumer_service.verify_consumer_details'


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

success_response = asyncapi_message_for_success_response(TASK_NAME)
