
# Saga pattern for microservices example - with timeouts

It's basically an implementation of CreateOrderSaga from [Chris Richardson book on Microservices](https://microservices.io/book)

In repo, we have `order_service` which is the saga entrypoint, 
and 3 other services with workers handling commands that `order_service` sends : `consumer_service`, `restaurant_service`, `accounting_service`.

For basic saga pattern, [saga_py](https://github.com/flowpl/saga_py) library is used.

# Run
Firstly, run all infrastructure 
```
docker-compose up --build --remove-orphans
```

Then, you can visit next URLs:
 * http://localhost:5000 - homepage with all links to run sagas.
 * http://localhost:8081 - AsyncAPI docs for `order_service`
 * http://localhost:8082 - AsyncAPI docs for `consumer_service`
 * http://localhost:8083 - AsyncAPI docs for `restaurant_service`
 * http://localhost:8084 - AsyncAPI docs for `accounting_service`


# Local development
Firstly, run RabbitMQ and Redis
```
docker-compose  --file docker-compose.local.yaml up 
```

To run each service, see `readme.md` files in each service folder. 

# Implementation details
## Common code, async messages and documentation  
In REST, we have Swagger / OpenAPI.
In async messaging, alternative is [AsyncAPI standard](https://www.asyncapi.com/) 
which provides its own IDL (interface definition language) for describing messages between various services.

Each service has its own AsyncAPI spec (see `asyncapi_specification.py` files) 
which generates specs using [asyncapi-python](https://github.com/dutradda/asyncapi-python) library.

[asyncapi-python](https://github.com/dutradda/asyncapi-python) library is also used for describing message schemas 
using dataclasses. 
For example, [`create_ticket_message.py`](app_common/messaging/restaurant_service_messaging/create_ticket_message.py) file looks like
```python
import dataclasses
from typing import List

import asyncapi


TASK_NAME = 'restaurant_service.create_ticket'


@dataclasses.dataclass
class OrderItem:
    name: str
    quantity: int


# "request" schema
@dataclasses.dataclass
class Payload:
    order_id: int
    customer_id: int
    items: List[OrderItem]


# "response" schema
@dataclasses.dataclass
class Response:
    ticket_id: int


message = asyncapi.Message(
    name=TASK_NAME,
    title='Create restaurant ticket',
    summary='This command creates ticket so restaurant knows order details. \n'
            'In real world, ticket may be created automatically or after restaurant manager approves it '
            '(confirm that they will be able to cook desired dishes)',
    payload=Payload,
)

response = asyncapi.Message(
    name=f'{TASK_NAME}.response',
    title='Response is just created restaurant ticket ID',
    payload=Response,
)
```

These schemas are used to generate AsyncAPI specification, e.g., (see [restaurant_service/restaurant_service/asyncapi_specification.py](restaurant_service/restaurant_service/asyncapi_specification.py))
```python
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
    servers={'development': asyncapi.Server(
        url='localhost',
        protocol=asyncapi.ProtocolType.REDIS,
        description='Development Broker Server',
    )},
)
```

All such schemas are common for a service that sends, and a service that handles messages, that's why
they're moved to `app_common` folder.

## Timeouts
This example app uses request/asynchronous response interaction style, 
i.e. it firstly sends "command" message to message broker (RabbitMQ), 
then waits for the response for some period of time. 
If response isn't returned, exception is raised.

Because we're in Python world, we have Celery which cares about all implementation, 
so end code looks like (see [order_service/order_service/app.py](order_service/order_service/app.py)):

```python
def create_restaurant_ticket(self):
    logging.info('Sending "create restaurant ticket" command ...')
    task_result = celery_app.send_task(
        create_ticket_message.TASK_NAME,
        args=[asdict(
            create_ticket_message.Payload(
                order_id=self.order.id,
                customer_id=self.order.consumer_id,
                items=[
                    create_ticket_message.OrderItem(
                        name=item.name,
                        quantity=item.quantity
                    )
                    for item in self.order.items
                ]
            )
        )],
        queue=restaurant_service_messaging.COMMANDS_QUEUE)

    self.saga_state.update(status=CreateOrderSagaStatuses.CREATING_RESTAURANT_TICKET,
                           last_message_id=task_result.id)

    response = create_ticket_message.Response(**task_result.get(timeout=self.TIMEOUT))
    logging.info(f'Restaurant ticket # {response.ticket_id} created')
    self.order.update(restaurant_ticket_id=response.ticket_id)
```