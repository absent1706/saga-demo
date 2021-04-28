from functools import partial

import asyncapi
from saga_framework.asyncapi_utils import \
    message_to_channel, \
    fake_asyncapi_servers, asyncapi_components_from_asyncapi_channels

from order_service.app_common.messaging import consumer_service_messaging, \
    accounting_service_messaging
from order_service.app_common.messaging.accounting_service_messaging import \
    authorize_card_message
from order_service.app_common.messaging.consumer_service_messaging import \
    verify_consumer_details_message
from order_service.app_common.messaging.restaurant_service_messaging import \
    create_ticket_message, reject_ticket_message, approve_ticket_message

"""
IMPORTANT!
We do NOT document error responses such as `restaurant_service.create_ticket.response.failure`
We assume that they have standard format (see SagaErrorPayload dataclass) 
"""
message_to_channel_publish_first = partial(message_to_channel, publish_made_first=True)
channels = dict([
    # verify consumer step
    message_to_channel_publish_first(verify_consumer_details_message.message,
                                     verify_consumer_details_message.success_response),

    # create/reject restaurant ticket step
    message_to_channel_publish_first(create_ticket_message.message,
                                     create_ticket_message.success_response),
    message_to_channel_publish_first(reject_ticket_message.message),  # compensation step has no resppnse

    # authorize card step
    message_to_channel_publish_first(authorize_card_message.message,
                                     authorize_card_message.success_response),

    # approve restaurant ticket step
    message_to_channel_publish_first(approve_ticket_message.message,
                                     approve_ticket_message.success_response),
])

spec = asyncapi.Specification(
    info=asyncapi.Info(
        title='Order service', version='1.0.0',
        description=f'Orchestrates CreateOrder saga. \n'
                    f' Publishes command messages to '
                    f'"{consumer_service_messaging.COMMANDS_QUEUE}", '
                    f'"{consumer_service_messaging.COMMANDS_QUEUE}", '
                    f'"{accounting_service_messaging.COMMANDS_QUEUE}" '
                    f' queues',
    ),
    channels=channels,
    # all messages met in specification
    components=asyncapi_components_from_asyncapi_channels(channels.values()),
    servers=fake_asyncapi_servers,
)


if __name__ == '__main__':
    import yaml
    from asyncapi.docs import spec_asjson

    print(yaml.dump(spec_asjson(spec)))
