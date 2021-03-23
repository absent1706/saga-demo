import asyncapi

from order_service.app_common.messaging.accounting_service_messaging import \
    authorize_card_message
from order_service.app_common.messaging.consumer_service_messaging import \
    verify_consumer_details_message
from order_service.app_common.messaging import consumer_service_messaging, restaurant_service_messaging, accounting_service_messaging
from order_service.app_common.messaging.asyncapi_utils import message_to_channel, message_to_component
from order_service.app_common.messaging.restaurant_service_messaging import \
    create_ticket_message, reject_ticket_message, approve_ticket_message
from order_service.app_common.messaging.asyncapi_utils import fake_asyncapi_servers

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
    channels=dict([
        # verify consumer step
        message_to_channel(verify_consumer_details_message.message, publish_made_first=True),
        # create/reject restaurant ticket step
        message_to_channel(create_ticket_message.message,
                           create_ticket_message.response, publish_made_first=True),
        message_to_channel(reject_ticket_message.message, publish_made_first=True),
        # authorize card step
        message_to_channel(authorize_card_message.message,
                           authorize_card_message.response, publish_made_first=True),
        # approve restaurant ticket step
        message_to_channel(approve_ticket_message.message, publish_made_first=True),
    ]),

    # all messages met in specification
    components=asyncapi.Components(messages=dict([
        message_to_component(verify_consumer_details_message.message),
        message_to_component(create_ticket_message.message),
        message_to_component(create_ticket_message.response),
        message_to_component(reject_ticket_message.message),
        message_to_component(authorize_card_message.message),
        message_to_component(approve_ticket_message.message)
    ])),
    servers=fake_asyncapi_servers,
)


if __name__ == '__main__':
    import yaml
    from asyncapi.docs import spec_asjson

    print(yaml.dump(spec_asjson(spec)))
