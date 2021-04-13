import asyncapi

from accounting_service.app_common.messaging import accounting_service_messaging
from accounting_service.app_common.messaging.accounting_service_messaging import \
    authorize_card_message
from accounting_service.app_common.sagas_framework.asyncapi_utils import \
    message_to_channel, fake_asyncapi_servers, \
    asyncapi_components_from_asyncapi_channels

"""
IMPORTANT!
We do NOT document error responses such as `restaurant_service.create_ticket.response.failure`
We assume that they have standard format (see SagaErrorPayload dataclass) 
"""
channels = dict([
    message_to_channel(authorize_card_message.message,
                       authorize_card_message.success_response)
])

spec = asyncapi.Specification(
    info=asyncapi.Info(
        title='Consumer service', version='1.0.0',
        description=f'Takes command messages from "{accounting_service_messaging.COMMANDS_QUEUE}" queue',
    ),
    channels=channels,
    components=asyncapi_components_from_asyncapi_channels(channels.values()),
    servers=fake_asyncapi_servers,
)

if __name__ == '__main__':
    import yaml
    from asyncapi.docs import spec_asjson

    print(yaml.dump(spec_asjson(spec)))
