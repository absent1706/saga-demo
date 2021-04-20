
# Saga pattern for microservices example

It's basically an implementation of CreateOrderSaga from [Chris Richardson book on Microservices](https://microservices.io/book)

**Table of contents**:
- [Running an app](#running-an-app)
- [Local development](#local-development)
- [Architecture](#architecture)
  * [Interface / Launcher](#interface---launcher)
  * [Saga Handler Services](#saga-handler-services)
  * [Orchestrator](#orchestrator)
- [Implementation details](#implementation-details)
  * [AsyncAPI documentation](#asyncapi-documentation)
  * [Common files](#common-files)


# Running an app
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


# Architecture
See more detailed architecture description at **TODO: insert a link to saga_framework**

Anyways, let's describe an architecure of this app.

Whole ecosystem for this app includes next main components

## Interface / Launcher 
`order_service` Flask app which is the saga entrypoint needed just to initiate saga runs. 

```python
def _run_saga(input_data):
    order = Order.create(**input_data)
    saga_state = CreateOrderSagaState.create(order_id=order.id)
    CreateOrderSaga(main_celery_app, saga_state.id).execute()
    return f'Scheduled saga #{saga_state.id}. ' \
           f'See its progress in order_service worker'
```

Here's saga definition 
```python

class CreateOrderSaga(StatefulSaga):
    saga_state_repository = CreateOrderSagaRepository()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.steps = [
            SyncStep(
                name='reject_order',
                compensation=self.reject_order
            ),
            
            AsyncStep(
                name='verify_consumer_details',
                action=self.verify_consumer_details,

                base_task_name=verify_consumer_details_message.TASK_NAME,
                queue=consumer_service_messaging.COMMANDS_QUEUE,

                on_success=self.verify_consumer_details_on_success,
                on_failure=self.verify_consumer_details_on_failure
            ),

            AsyncStep(
                name='create_restaurant_ticket',
                action=self.create_restaurant_ticket,
                compensation=self.reject_restaurant_ticket,

                base_task_name=create_ticket_message.TASK_NAME,
                queue=restaurant_service_messaging.COMMANDS_QUEUE,

                on_success=self.create_restaurant_ticket_on_success,
                on_failure=self.create_restaurant_ticket_on_failure
            ),
            # other steps ...
        ]
    
    # method implementation goes next ...
```

Initiating a saga means simply sending first Celery task to Saga Handler Service:

```python
class CreateOrderSaga(StatefulSaga):
    # other code ...
    
    def verify_consumer_details(self, current_step: AsyncStep):
        logging.info(f'Verifying consumer #{self.saga_state.order.consumer_id} ...')

        message_id = self.send_message_to_other_service(
            current_step,
            asdict(
                verify_consumer_details_message.Payload(
                    consumer_id=self.saga_state.order.consumer_id
                )
            )
        )

        self.saga_state_repository.update(self.saga_id, last_message_id=message_id)

```


## Saga Handler Services 
`consumer_service`, `restaurant_service`, `accounting_service`. 

They all have Celery workers that handle saga steps and report results to Orchestrator.

Results are sent as a Celery tasks, for example:
```python
@command_handlers_celery_app.task(bind=True, name=create_ticket_message.TASK_NAME)
@saga_step_handler(response_queue=CREATE_ORDER_SAGA_RESPONSE_QUEUE)
def create_ticket_task(self: Task, saga_id: int, payload: dict) -> dict:
    request_data = create_ticket_message.Payload(**payload)

    # in real world, we would create a ticket in restaurant service DB
    # here, we will just generate some fake ID of just created ticket
    ticket_id = random.randint(200, 300)
    logging.info(f'Restaurant ticket {request_data} created')
    logging.info(f'Ticket details: {payload}')

    return asdict(create_ticket_message.Response(
        ticket_id=ticket_id
    ))
```

Here, `saga_step_handler` decorator sends payload (that our function returns) to `CREATE_ORDER_SAGA_RESPONSE_QUEUE`.

> Response task names are computed based on initial task names (see `success_task_name` and `failure_task_name` functions).
> For example, for "request" Celery task named `restaurant_service.create_ticket`, corresponding "response" Celery task (which will be handled by Orchestrator) will be named as `restaurant_service.create_ticket.response.success`

## Orchestrator

`order_service` worker, the heart of saga orchestration. 

It listens to replies from Saga Handler Services, does certain actions like
```python
    def create_restaurant_ticket_on_success(self, step: BaseStep, payload: dict):
        response = create_ticket_message.Response(**payload)
        logging.info(f'Restaurant ticket # {response.ticket_id} created')

        self.saga_state.order.update(restaurant_ticket_id=response.ticket_id)
```

, and launches next saga step (or rolls back a saga if error occured).

See more details at **TODO: insert a link to saga_framework**

Handling replies from Saga Handler Services is also implemented with Celery.
Corresponding Celery are registered automatically with `CreateOrderSaga.register_async_step_handlers()`, 
see [`create_order_saga_worker.py` file](order_service/order_service/create_order_saga_worker.py)
 

# Implementation details
## AsyncAPI documentation  
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

from ...sagas_framework.asyncapi_utils import \
    asyncapi_message_for_success_response

TASK_NAME = 'restaurant_service.create_ticket'


@dataclasses.dataclass
class OrderItem:
    name: str
    quantity: int


@dataclasses.dataclass
class Payload:
    order_id: int
    customer_id: int
    items: List[OrderItem]


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

success_response = asyncapi_message_for_success_response(
    TASK_NAME,
    title='Ticket ID is returned',
    payload_dataclass=Response
)
```

These schemas are used to generate AsyncAPI specification, e.g., (see [restaurant_service/restaurant_service/asyncapi_specification.py](restaurant_service/restaurant_service/asyncapi_specification.py))
```python
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
```

## Common files
Async messages sent between services are used by both orchestrator (`order_service`) and handler services ().

So, messages are described in `app_common` folder that's shared between the services.

> Ideally, there should be no common folder, but either sub-repository or, even better, 
>  internal Python package with its own versioning.
> However, in this demo project, we simply have shared folder
