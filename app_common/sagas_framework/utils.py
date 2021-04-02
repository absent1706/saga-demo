from dataclasses import dataclass, asdict

from celery import Celery, Task


def success_task_name(task_name: str):
    return f'{task_name}.response.success'


def failure_task_name(task_name: str):
    return f'{task_name}.response.failure'
