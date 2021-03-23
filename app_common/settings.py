import os

CELERY_BROKER = os.getenv('CELERY_BROKER', 'pyamqp://rabbitmq:rabbitmq@localhost//')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'rpc://')
