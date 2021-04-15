import os

CELERY_BROKER = os.getenv('CELERY_BROKER', 'pyamqp://rabbitmq:rabbitmq@localhost//')
