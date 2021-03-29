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
from sqlalchemy_mixins import AllFeaturesMixin

from order_service.app_common import settings
from order_service.app_common.messaging.accounting_service_messaging import \
    authorize_card_message
from order_service.app_common.messaging.consumer_service_messaging import \
    verify_consumer_details_message
from order_service.app_common.messaging import consumer_service_messaging, \
    accounting_service_messaging, restaurant_service_messaging
from order_service.app_common.sagas_framework import BaseSaga, SyncStep, AsyncStep

logging.basicConfig(level=logging.DEBUG)

main_celery_app = Celery('my_celery_app', broker=settings.CELERY_BROKER)

app = Flask(__name__)

current_dir = os.path.abspath(os.path.dirname(__file__))
app.config[
    'SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{current_dir}/order_service.sqlite"

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


class CreateOrderSagaStatuses(enum.Enum):
    ORDER_CREATED = 'ORDER_CREATED'
    VERIFYING_CONSUMER_DETAILS = 'VERIFYING_CONSUMER_DETAILS'
    CREATING_RESTAURANT_TICKET = 'CREATING_RESTAURANT_TICKET'
    APPROVING_RESTAURANT_TICKET = 'APPROVING_RESTAURANT_TICKET'
    AUTHORIZING_CREDIT_CARD = 'AUTHORIZING_CREDIT_CARD'
    SUCCEEDED = 'SUCCEEDED'

    REJECTING_RESTAURANT_TICKET = 'REJECTING_RESTAURANT_TICKET'
    FAILED = 'FAILED'


class CreateOrderSagaState(BaseModel):
    id = db.Column(db.Integer, primary_key=True)
    last_message_id = db.Column(db.String)

    status = db.Column(db.Enum(CreateOrderSagaStatuses),
                       default=CreateOrderSagaStatuses.ORDER_CREATED)
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
        price=random.randint(10, 100),
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


class SqlAlchemySaga(BaseSaga):
    """
    Note this class assumes sqlalchemy-mixins library is used.
    Use it rather as an example
    """
    saga_state_cls = None  # SQLAlchemy class (must use sqlalchemy-mixins)
    _saga_state = None  # cached SQLAlchemy instance

    @property
    def saga_state(self):
        if not self._saga_state:
            self._saga_state = self.saga_state_cls.find(self.saga_id)

        return self._saga_state


class CreateOrderSaga(SqlAlchemySaga):
    saga_state_cls = CreateOrderSagaState

    def __init__(self, celery_app: Celery, saga_id: int):
        super().__init__(celery_app, saga_id)

        self.steps = [
            SyncStep(
                name='reject order',
                compensation=self.reject_order
            ),
            AsyncStep(
                name='verify consumer details',
                action=self.verify_consumer_details,

                base_task_name=verify_consumer_details_message.TASK_NAME,
                queue=consumer_service_messaging.COMMANDS_QUEUE,

                on_success=self.verify_consumer_details_on_success,
                on_failure=self.verify_consumer_details_on_failure,
            )

            # .action(self.create_restaurant_ticket, self.reject_restaurant_ticket) \
            # .action(self.authorize_card, self.NO_ACTION) \
            # .action(self.approve_restaurant_ticket, self.NO_ACTION) \
            # .action(self.approve_order, self.NO_ACTION) \
        ]

    def verify_consumer_details(self, step: AsyncStep):
        logging.info(f'Verifying consumer #{self.saga_state.order.consumer_id} ...')

        message_id = self.send_message_to_other_service(
            step,
            asdict(
                verify_consumer_details_message.Payload(
                    consumer_id=self.saga_state.order.consumer_id
                )
            )
        )

        self.saga_state.update(status=CreateOrderSagaStatuses.VERIFYING_CONSUMER_DETAILS,
                               last_message_id=message_id)

    def verify_consumer_details_on_success(self, payload):
        logging.info(f'Consumer #{self.saga_state.order.consumer_id} verification succeeded')
        logging.info(f'result = {payload}')

    def verify_consumer_details_on_failure(self, payload):
        logging.info(f'Consumer #{self.saga_state.order.consumer_id} verification failed')
        logging.info(f'result = {payload}')

    def reject_order(self, step):
        self.saga_state.order.update(status=OrderStatuses.REJECTED)
        logging.info(f'Compensation: order {self.saga_state.order.id} rejected')

    def on_saga_success(self):
        self.saga_state.update(status=CreateOrderSagaStatuses.SUCCEEDED)

        logging.info(f'Saga {self.saga_id} succeeded')

    def on_saga_failure(self, initial_failure_payload: dict):
        self.saga_state.update(status=CreateOrderSagaStatuses.FAILED)

        logging.info(f'Saga {self.saga_id} failed. \n'
                     f'Initial failure details: {initial_failure_payload}')

    # def create_restaurant_ticket(self):
    #     logging.info('Sending "create restaurant ticket" command ...')
    #     task_result = main_celery_app.send_task(
    #         create_ticket_message.TASK_NAME,
    #         args=[asdict(
    #             create_ticket_message.Payload(
    #                 order_id=self.order.id,
    #                 customer_id=self.order.consumer_id,
    #                 items=[
    #                     create_ticket_message.OrderItem(
    #                         name=item.name,
    #                         quantity=item.quantity
    #                     )
    #                     for item in self.order.items
    #                 ]
    #             )
    #         )],
    #         queue=restaurant_service_messaging.COMMANDS_QUEUE)
    #
    #     self.saga_state.update(status=CreateOrderSagaStatuses.CREATING_RESTAURANT_TICKET,
    #                            last_message_id=task_result.id)
    #
    #     # It's safe to assume success case.
    #     # In case task handler throws exception,
    #     #   Celery automatically raises exception here by itself,
    #     #   and saga library automatically launches compensations
    #     response = create_ticket_message.Response(**task_result.get(timeout=self.TIMEOUT))
    #     logging.info(f'Restaurant ticket # {response.ticket_id} created')
    #     self.order.update(restaurant_ticket_id=response.ticket_id)
    #
    # def reject_restaurant_ticket(self):
    #     logging.info(f'Compensation: rejecting restaurant ticket #{self.order.restaurant_ticket_id} ...')
    #     task_result = main_celery_app.send_task(
    #         reject_ticket_message.TASK_NAME,
    #         args=[asdict(
    #             reject_ticket_message.Payload(
    #                 ticket_id=self.order.restaurant_ticket_id
    #             )
    #         )],
    #         queue=restaurant_service_messaging.COMMANDS_QUEUE)
    #
    #     self.saga_state.update(status=CreateOrderSagaStatuses.REJECTING_RESTAURANT_TICKET,
    #                            last_message_id=task_result.id)
    #
    #     task_result.get(timeout=self.TIMEOUT)
    #     logging.info(f'Compensation: restaurant ticket #{self.order.restaurant_ticket_id} rejected')
    #
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
    #     self.saga_state.update(status=CreateOrderSagaStatuses.APPROVING_RESTAURANT_TICKET,
    #                            last_message_id=task_result.id)
    #
    #     task_result.get(timeout=self.TIMEOUT)
    #     logging.info(f'Compensation: restaurant ticket #{self.order.restaurant_ticket_id} approved')
    #
    # def authorize_card(self):
    #     logging.info(f'Authorizing card (amount={self.order.price}) ...')
    #     task_result = main_celery_app.send_task(
    #         authorize_card_message.TASK_NAME,
    #         args=[asdict(
    #             authorize_card_message.Payload(card_id=self.order.card_id,
    #                                            amount=self.order.price)
    #         )],
    #         queue=accounting_service_messaging.COMMANDS_QUEUE)
    #
    #     self.saga_state.update(status=CreateOrderSagaStatuses.AUTHORIZING_CREDIT_CARD,
    #                            last_message_id=task_result.id)
    #
    #     # It's safe to assume success case.
    #     # In case task handler throws exception,
    #     #   Celery automatically raises exception here by itself,
    #     #   and saga library automatically launches compensations
    #     response = authorize_card_message.Response(**task_result.get(timeout=self.TIMEOUT))
    #     logging.info(f'Card authorized. Transaction ID: {response.transaction_id}')
    #     self.order.update(transaction_id=response.transaction_id)
    #
    # def approve_order(self):
    #     self.order.update(status=OrderStatuses.APPROVED)
    #     self.saga_state.update(status=CreateOrderSagaStatuses.SUCCEEDED, last_message_id=None)
    #
    #     logging.info(f'Order {self.order.id} approved')


if __name__ == '__main__':
    result = run_random_saga()
