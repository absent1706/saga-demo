import asyncapi
from saga_framework.asyncapi_utils import \
    message_to_channel, fake_asyncapi_servers, \
    asyncapi_components_from_asyncapi_channels

from restaurant_service.app_common.messaging import restaurant_service_messaging
from restaurant_service.app_common.messaging.restaurant_service_messaging import \
    create_ticket_message, reject_ticket_message, approve_ticket_message

"""
IMPORTANT!
We do NOT document error responses such as `restaurant_service.create_ticket.response.failure`
We assume that they have standard format (see SagaErrorPayload dataclass) 
"""
channels = dict([
    message_to_channel(create_ticket_message.message,
                       create_ticket_message.success_response),
    message_to_channel(reject_ticket_message.message),  # compensation step has no resppnse
    message_to_channel(approve_ticket_message.message,
                       approve_ticket_message.success_response),
])

spec = asyncapi.Specification(
    info=asyncapi.Info(
        title='Restaurant service', version='1.0.0',
        description=f'Takes command messages from "{restaurant_service_messaging.COMMANDS_QUEUE}" queue',
    ),
    channels=channels,
    components=asyncapi_components_from_asyncapi_channels(channels.values()),
    servers=fake_asyncapi_servers,
)

if __name__ == '__main__':
    import yaml
    from asyncapi.docs import spec_asjson

    print(yaml.dump(spec_asjson(spec)))
