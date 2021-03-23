import asyncapi

from accounting_service.app_common.messaging.asyncapi_utils import message_to_channel, message_to_component, fake_asyncapi_servers
from accounting_service.app_common.messaging.accounting_service_messaging import authorize_card_message
from accounting_service.app_common.messaging import accounting_service_messaging

spec = asyncapi.Specification(
    info=asyncapi.Info(
        title='Consumer service', version='1.0.0',
        description=f'Takes command messages from "{accounting_service_messaging.COMMANDS_QUEUE}" queue',
    ),
    channels=dict([
        message_to_channel(authorize_card_message.message,
                           authorize_card_message.response)
    ]),
    # all messages met in specification
    components=asyncapi.Components(messages=dict([
        message_to_component(authorize_card_message.message),
        message_to_component(authorize_card_message.response)
    ])),
    servers=fake_asyncapi_servers,
)

if __name__ == '__main__':
    import yaml
    from asyncapi.docs import spec_asjson

    print(yaml.dump(spec_asjson(spec)))
