# Setup
```
pipenv --python 3.8
pipenv install
pipenv run pip install 'asyncapi[http,yaml,redis,subscriber,docs]'
```

# Run
```
PYTHONPATH=. FLASK_DEBUG=1 FLASK_APP=order_service/app.py pipenv run flask run

```

or simply 
```
PYTHONPATH=. python order_service/app.py
```


# Run Celery worker (to listen for saga replies)
This worker is the heart of saga orchestration.
It runs Celery worker for the tasks that were registered automatically with `CreateOrderSaga.register_async_step_handlers()`

```
./run_worker.sh 
```

# Run API docs server 
```
PYTHONPATH=. asyncapi-docs --api-module order_service.asyncapi_specification

curl http://127.0.0.1:5000/asyncapi.yaml
```