import asyncapi

from restaurant_service.app_common.messaging import restaurant_service_messaging
from restaurant_service.app_common.messaging.asyncapi_utils import message_to_channel, message_to_component, fake_asyncapi_servers
from restaurant_service.app_common.messaging.restaurant_service_messaging import \
    create_ticket_message, reject_ticket_message, approve_ticket_message

spec = asyncapi.Specification(
    info=asyncapi.Info(
        title='Restaurant service', version='1.0.0',
        description=f'Takes command messages from "{restaurant_service_messaging.COMMANDS_QUEUE}" queue',
    ),
    channels=dict([
        message_to_channel(create_ticket_message.message,
                           create_ticket_message.response),
        message_to_channel(reject_ticket_message.message),
        message_to_channel(approve_ticket_message.message),
    ]),
    # all messages met in specification
    components=asyncapi.Components(messages=dict([
        message_to_component(create_ticket_message.message),
        message_to_component(create_ticket_message.response),
        message_to_component(reject_ticket_message.message),
        message_to_component(approve_ticket_message.message)
    ])),
    servers=fake_asyncapi_servers,
)

if __name__ == '__main__':
    import yaml
    from asyncapi.docs import spec_asjson

    print(yaml.dump(spec_asjson(spec)))
