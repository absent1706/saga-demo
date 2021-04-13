import asyncapi

from consumer_service.app_common.messaging import consumer_service_messaging
from consumer_service.app_common.messaging.consumer_service_messaging import \
    verify_consumer_details_message
from consumer_service.app_common.sagas_framework.asyncapi_utils import \
    fake_asyncapi_servers, \
    message_to_channel, asyncapi_components_from_asyncapi_channels

"""
IMPORTANT!
We do NOT document error responses such as `restaurant_service.create_ticket.response.failure`
We assume that they have standard format (see SagaErrorPayload dataclass) 
"""
channels = dict([
    message_to_channel(verify_consumer_details_message.message,
                       verify_consumer_details_message.success_response)
])

spec = asyncapi.Specification(
    info=asyncapi.Info(
        title='Consumer service', version='1.0.0',
        description=f'Takes command messages from "{consumer_service_messaging.COMMANDS_QUEUE}" queue',
    ),
    channels=channels,
    components=asyncapi_components_from_asyncapi_channels(channels.values()),
    servers=fake_asyncapi_servers,
)


if __name__ == '__main__':
    import yaml
    from asyncapi.docs import spec_asjson

    print(yaml.dump(spec_asjson(spec)))
