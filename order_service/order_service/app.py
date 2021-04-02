import abc
import enum
import logging
import os
import random
import traceback

import mimesis  # for fake data generation
from dataclasses import asdict

from celery import Celery
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import Session
from sqlalchemy_mixins import AllFeaturesMixin

from order_service.app_common import settings
from order_service.app_common.messaging.accounting_service_messaging import \
    authorize_card_message
from order_service.app_common.messaging.consumer_service_messaging import \
    verify_consumer_details_message
from order_service.app_common.messaging import consumer_service_messaging, \
    accounting_service_messaging, restaurant_service_messaging
from order_service.app_common.messaging.restaurant_service_messaging import \
    create_ticket_message, reject_ticket_message
from order_service.app_common.sagas_framework import BaseSaga, SyncStep, \
    AsyncStep, BaseStep, AbstractSagaStateRepository, StatefulSaga

logging.basicConfig(level=logging.DEBUG)

main_celery_app = Celery('my_celery_app', broker=settings.CELERY_BROKER)

app = Flask(__name__)

current_dir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{current_dir}/order_service.sqlite"

db = SQLAlchemy(app, session_options={'autocommit': True})


class OrderStatuses(enum.Enum):
    PENDING_VALIDATION = 'pending_validation'
    APPROVED = 'approved'
    REJECTED = 'rejected'


class BaseModel(db.Model, AllFeaturesMixin):
    __abstract__ = True
    pass


class Order(BaseModel):
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.Enum(OrderStatuses),
                       default=OrderStatuses.PENDING_VALIDATION)
    consumer_id = db.Column(db.Integer)
    card_id = db.Column(db.Integer)
    price = db.Column(db.Integer)

    items = db.relationship("OrderItem", backref="order")

    transaction_id = db.Column(db.String)
    restaurant_ticket_id = db.Column(db.Integer)


class OrderItem(BaseModel):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'))
    name = db.Column(db.String)
    quantity = db.Column(db.Integer)


class CreateOrderSagaState(BaseModel):
    id = db.Column(db.Integer, primary_key=True)
    last_message_id = db.Column(db.String)

    status = db.Column(db.String, default='not_started')
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'))
    order = db.relationship("Order")


BaseModel.set_session(db.session)
db.create_all()  # "run migrations"


@app.route('/ping')
def ping():
    return 'ping response'


BASE_INPUT_DATA = dict(
    items=[
        OrderItem(
           name=mimesis.Food().dish(),  # some fake dish name
           quantity=random.randint(1, 5)
        ),
        OrderItem(
            name=mimesis.Food().dish(),  # some fake dish name
            quantity=random.randint(1, 5)
        )
    ]
)

# magic numbers that make consumer_service succeed or fail
CONSUMER_ID_THAT_WILL_SUCCEED = 70
CONSUMER_ID_THAT_WILL_FAIL = 10
CONSUMER_ID_THAT_WILL_FAIL_BECAUSE_OF_TIMEOUT = 55

# magic numbers that make accounting_service succeed or fail
PRICE_THAT_WILL_SUCCEED = 20
PRICE_THAT_WILL_FAIL = 80


def _run_saga(input_data):
    order = Order.create(**input_data)
    saga_state = CreateOrderSagaState.create(order_id=order.id)
    CreateOrderSaga(main_celery_app, saga_state.id).execute()


@app.route('/')
def welcome_page():
    return '''
    Welcome to saga orchestration demo!
    You can use next endpoints to start Order Create saga:
    <ul>
      <li><a href="/run-random-saga">/run-random-saga</a></li>
      <li><a href="/run-success-saga">/run-success-saga</a></li>
      <li><a href="/run-saga-failing-on-consumer-verification-because-of-incorrect-id">/run-saga-failing-on-consumer-verification-because-of-incorrect-id</a></li>
      <li><a href="/run-saga-failing-on-consumer-verification-because-of-timeout">/run-saga-failing-on-consumer-verification-because-of-timeout</a></li>
      <li><a href="/run-saga-failing-on-card-authorization">/run-saga-failing-on-card-authorization</a></li>
    </ul>
    '''


@app.route('/run-random-saga')
def run_random_saga():
    # it will randomly pass or fail
    return _run_saga(input_data=dict(
        **BASE_INPUT_DATA,
        consumer_id=random.randint(1, 100),
        price=PRICE_THAT_WILL_FAIL,
        card_id=random.randint(1, 5)
    ))


@app.route('/run-success-saga')
def run_success_saga():
    # it should succeed
    return _run_saga(input_data=dict(
        **BASE_INPUT_DATA,
        consumer_id=CONSUMER_ID_THAT_WILL_SUCCEED,
        price=PRICE_THAT_WILL_SUCCEED,
        card_id=random.randint(1, 5)
    ))


# @app.route('/run-saga-failing-on-consumer-verification-because-of-incorrect-id')
# def run_saga_failing_on_consumer_verification_incorrect_id():
#     # it should fail on consumer verification stage
#     return _run_saga(input_data=dict(
#         **BASE_INPUT_DATA,
#         consumer_id=CONSUMER_ID_THAT_WILL_FAIL,
#         price=PRICE_THAT_WILL_SUCCEED,
#         card_id=random.randint(1, 5)
#     ))
#
#
# @app.route('/run-saga-failing-on-consumer-verification-because-of-timeout')
# def run_saga_failing_on_consumer_verification_timeout():
#     # it should fail on consumer verification stage
#     return _run_saga(input_data=dict(
#         **BASE_INPUT_DATA,
#         consumer_id=CONSUMER_ID_THAT_WILL_FAIL_BECAUSE_OF_TIMEOUT,
#         price=PRICE_THAT_WILL_SUCCEED,
#         card_id=random.randint(1, 5)
#     ))
#
#
# @app.route('/run-saga-failing-on-card-authorization')
# def run_saga_failing_on_card_authorization():
#     # it should fail on card authorization stage
#     return _run_saga(input_data=dict(
#         **BASE_INPUT_DATA,
#         consumer_id=CONSUMER_ID_THAT_WILL_SUCCEED,
#         price=PRICE_THAT_WILL_FAIL,
#         card_id=random.randint(1, 5)
#     ))

class CreateOrderSagaRepository(AbstractSagaStateRepository):
    def get_saga_state_by_id(self, saga_id: int) -> CreateOrderSagaState:
        return CreateOrderSagaState.find(saga_id)

    def update_status(self, saga_id: int, status: str) -> CreateOrderSagaState:
        return self.get_saga_state_by_id(saga_id).update(status=status)

    def update(self, saga_id: int, **fields_to_update: str) -> object:
        return self.get_saga_state_by_id(saga_id).update(**fields_to_update)


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

            AsyncStep(
                name='authorize_card',
                action=self.authorize_card,

                base_task_name=authorize_card_message.TASK_NAME,
                queue=accounting_service_messaging.COMMANDS_QUEUE,

                on_success=self.authorize_card_on_success,
                on_failure=self.authorize_card_on_failure
            )
            # .action(self.approve_restaurant_ticket, self.NO_ACTION) \
            # .action(self.approve_order, self.NO_ACTION) \
        ]

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

    def verify_consumer_details_on_success(self, step: BaseStep, payload: dict):
        logging.info(f'Consumer #{self.saga_state.order.consumer_id} verification succeeded')
        logging.info(f'result = {payload}')

    def verify_consumer_details_on_failure(self, step: BaseStep, payload: dict):
        logging.info(f'Consumer #{self.saga_state.order.consumer_id} verification failed')
        logging.info(f'result = {payload}')

    def reject_order(self, step: BaseStep):
        self.saga_state.order.update(status=OrderStatuses.REJECTED)
        logging.info(f'Compensation: order {self.saga_state.order.id} rejected')

    def create_restaurant_ticket(self, current_step: AsyncStep):
        logging.info(f'Creating restaurent ticket for saga {self.saga_id} ...')

        message_id = self.send_message_to_other_service(
            current_step,
            asdict(
                create_ticket_message.Payload(
                    order_id=self.saga_state.order.id,
                    customer_id=self.saga_state.order.consumer_id,
                    items=[
                        create_ticket_message.OrderItem(
                            name=item.name,
                            quantity=item.quantity
                        )
                        for item in self.saga_state.order.items
                    ]
                )
            )
        )

        self.saga_state_repository.update(self.saga_id, last_message_id=message_id)

    def create_restaurant_ticket_on_success(self, step: BaseStep, payload: dict):
        response = create_ticket_message.Response(**payload)
        logging.info(f'Restaurant ticket # {response.ticket_id} created')

        self.saga_state.order.update(restaurant_ticket_id=response.ticket_id)

    def create_restaurant_ticket_on_failure(self, step: BaseStep, payload: dict):
        logging.info(f'Restaurant ticket creation for saga {self.saga_id} failed: \n'
                     f'{payload}')

    def reject_restaurant_ticket(self, current_step: AsyncStep):
        logging.info(f'Compensation: rejecting restaurant ticket #{self.saga_state.order.restaurant_ticket_id} ...')

        message_id = self.send_message_to_other_service(
            current_step,
            asdict(
                reject_ticket_message.Payload(
                    ticket_id=self.saga_state.order.restaurant_ticket_id
                )
            ),
            # in compensation, it's needed to explicitly set Celery task name
            task_name=reject_ticket_message.TASK_NAME
        )

        self.saga_state_repository.update(self.saga_id, last_message_id=message_id)

    def authorize_card(self, current_step: AsyncStep):
        logging.info(f'Authorizing card for saga {self.saga_id} (amount={self.saga_state.order.price} ...')

        message_id = self.send_message_to_other_service(
            current_step,
            asdict(
                authorize_card_message.Payload(
                    card_id=self.saga_state.order.card_id,
                    amount=self.saga_state.order.price
                )
            )
        )

        self.saga_state_repository.update(self.saga_id, last_message_id=message_id)

    def authorize_card_on_success(self, step: BaseStep, payload: dict):
        response = authorize_card_message.Response(**payload)
        logging.info(f'Card authorized. Transaction ID: {response.transaction_id}')
        self.saga_state.order.update(transaction_id=response.transaction_id)

    def authorize_card_on_failure(self, step: BaseStep, payload: dict):
        logging.info(f'Card authorization for saga {self.saga_id} failed: \n'
                     f'{payload}')

    # def approve_restaurant_ticket(self):
    #     logging.info(f'Approving restaurant ticket #{self.order.restaurant_ticket_id} ...')
    #     task_result = main_celery_app.send_task(
    #         approve_ticket_message.TASK_NAME,
    #         args=[asdict(
    #             approve_ticket_message.Payload(
    #                 ticket_id=self.order.restaurant_ticket_id
    #             )
    #         )],
    #         queue=restaurant_service_messaging.COMMANDS_QUEUE)
    #
    #     self.saga_state_repository.update_status(self.saga_id, CreateOrderSagaStatuses.APPROVING_RESTAURANT_TICKET,
    #                            last_message_id=task_result.id)
    #
    #     task_result.get(timeout=self.TIMEOUT)
    #     logging.info(f'Compensation: restaurant ticket #{self.order.restaurant_ticket_id} approved')
    #
    # def approve_order(self):
    #     self.order.update(status=OrderStatuses.APPROVED)
    #     self.saga_state_repository.update_status(self.saga_id, CreateOrderSagaStatuses.SUCCEEDED, last_message_id=None)
    #
    #     logging.info(f'Order {self.order.id} approved')


if __name__ == '__main__':
    result = run_random_saga()
