PYTHONPATH=. pipenv run celery -A consumer_service.worker worker --loglevel=INFO