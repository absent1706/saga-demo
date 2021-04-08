import logging
import typing

from abc import ABC
from dataclasses import asdict

from celery import Celery, Task

from .utils import success_task_name, failure_task_name, serialize_saga_error


NO_ACTION = lambda *args: None
logger = logging.getLogger(__name__)


class BaseStep(ABC):
    def __init__(self,
                 name: str,
                 action: typing.Callable = NO_ACTION,
                 compensation: typing.Callable = NO_ACTION,
                 ):
        self.name = name
        self.action = action
        self.compensation = compensation


class SyncStep(BaseStep):
    pass


class AsyncStep(BaseStep):
    def __init__(self,
                 base_task_name: str,
                 queue: str,
                 on_success: typing.Callable = NO_ACTION,
                 on_failure: typing.Callable = NO_ACTION,
                 *args, **kwargs
                 ):
        self.base_task_name = base_task_name
        self.queue = queue
        self.on_success = on_success
        self.on_failure = on_failure

        super().__init__(*args, **kwargs)


class BaseSaga:
    saga_id: int = None
    steps: typing.List[BaseStep] = None
    celery_app: Celery = None

    def __init__(self, celery_app: Celery, saga_id: int):
        self.celery_app = celery_app
        self.saga_id = saga_id

    def get_first_step(self) -> BaseStep:
        return self.steps[0]

    def get_step_by_name(self, step_name: str) -> BaseStep:
        for step in self.steps:
            if step.name == step_name:
                return step

        raise KeyError(f'no step found with name {step_name}')

    def _get_step_index(self, step: BaseStep) -> int:
        for i in range(len(self.steps)):
            if self.steps[i].name == step.name:
                return i

        raise IndexError(f'step wasn\'t found')

    def _get_next_step(self, step: typing.Union[BaseStep, None]) -> typing.Union[BaseStep, None]:
        if not step:
            return self.steps[0]

        step_index = self._get_step_index(step)

        its_last_step = (step_index == len(self.steps) - 1)

        if its_last_step:
            return None
        else:
            return self.steps[step_index + 1]

    def _get_previous_step(self, step: typing.Union[BaseStep, None]) -> typing.Union[BaseStep, None]:
        step_index = self._get_step_index(step)

        its_first_step = (step_index == 0)

        if its_first_step:
            return None
        else:
            return self.steps[step_index - 1]

    def run_step(self, step: BaseStep):
        error_occured = False

        try:
            logger.info(f'Saga {self.saga_id}: '
                        f'running "{step.name}" step')
            step.action(step)
        except BaseException as exc:
            error_occured = True
            self.compensate(
                step,
                initial_failure_payload=asdict(serialize_saga_error(exc))
            )

        if not error_occured:
            # for sync steps, it's assumed we can run next step just after them
            # for async ones, we will wait for on_success or on_failure
            if isinstance(step, SyncStep):
                self.run_next_step_if_exists(step)

    def compensate_step(self, step: BaseStep, initial_failure_payload: dict):
        logger.info(f'Saga {self.saga_id}: '
                    f'compensating "{step.name}" step')
        step.compensation(step)

    def run_next_step_if_exists(self, step: BaseStep):
        next_step = self._get_next_step(step)
        if next_step:
            self.run_step(next_step)
        else:
            self.on_saga_success()

    def compensate_previous_step_if_exists(self, step: BaseStep, initial_failure_payload: dict):
        previous_step = self._get_previous_step(step)
        if previous_step:
            self.compensate_step(previous_step, initial_failure_payload)
        else:
            self.on_saga_failure(initial_failure_payload)

    def on_step_success(self, step: AsyncStep, payload: dict):
        logger.info(f'Saga {self.saga_id}: '
                    f'running on_success for "{step.name}" step')

        step.on_success(step, payload)
        self.run_next_step_if_exists(step)

    def on_step_failure(self, step: AsyncStep, payload: dict):
        logger.info(f'Saga {self.saga_id}: '
                    f'running on_failure for "{step.name}" step')

        step.on_failure(step, payload)
        self.compensate(step, payload)

    def compensate(self, failed_step: BaseStep, initial_failure_payload: dict = None):
        step = failed_step
        while step:
            self.compensate_step(step, initial_failure_payload)
            step = self._get_previous_step(step)

        self.on_saga_failure(initial_failure_payload)

    def execute(self):
        self.run_step(self.steps[0])

    @property
    def async_steps(self) -> typing.List[AsyncStep]:
        return [step for step in self.steps if isinstance(step, AsyncStep)]

    def get_async_step_by_success_task_name(self, success_task_name_: str) -> AsyncStep:
        for step in self.async_steps:
            if success_task_name(step.base_task_name) == success_task_name_:
                return step

        raise KeyError(f'no step found with success task name {success_task_name_}')

    def get_async_step_by_failure_task_name(self, failure_task_name_: str) -> AsyncStep:
        for step in self.async_steps:
            if failure_task_name(step.base_task_name) == failure_task_name_:
                return step

        raise KeyError(f'no step found with failure task name {failure_task_name_}')

    @classmethod
    def register_async_step_handlers(cls, celery_app: Celery):
        # noinspection PyTypeChecker
        dummy_saga_instance = cls(None, None)

        for step in dummy_saga_instance.async_steps:
            cls.register_success_handler_for_step(celery_app, step)
            cls.register_failure_handler_for_step(celery_app, step)

    @classmethod
    def register_success_handler_for_step(cls, celery_app: Celery,
                                          step: AsyncStep):
        def on_success_handler(celery_task: Task, saga_id: int, payload: dict):
            saga = cls(celery_app=celery_app, saga_id=saga_id)

            step_ = saga.get_async_step_by_success_task_name(celery_task.name)
            saga.on_step_success(step_, payload)

        celery_app.task(
            name=success_task_name(step.base_task_name),
            bind=True
        )(on_success_handler)

    @classmethod
    def register_failure_handler_for_step(cls, celery_app: Celery,
                                          step: AsyncStep):

        def on_failure_handler(celery_task: Task, saga_id: int, payload: dict):
            saga = cls(celery_app, saga_id)

            step_ = saga.get_async_step_by_failure_task_name(celery_task.name)
            saga.on_step_failure(step_, payload)

        celery_app.task(
            name=failure_task_name(step.base_task_name),
            bind=True
        )(on_failure_handler)

    def send_message_to_other_service(self, step: AsyncStep, payload: dict, task_name: str = None):
        task_result = self.celery_app.send_task(
            task_name or step.base_task_name,
            args=[
                self.saga_id,
                payload
            ],
            queue=step.queue
        )

        return task_result.id

    def on_saga_success(self):
        """
        This method runs when saga is fully completed with success
        """

        logger.info(f'Saga {self.saga_id} succeeded')

    def on_saga_failure(self, initial_failure_payload: dict):
        """
        This method runs when saga is failed (after lasy compensation runs)
        """
        logger.info(f'Saga {self.saga_id} failed. \n'
                    f'Initial failure details: {initial_failure_payload}')

