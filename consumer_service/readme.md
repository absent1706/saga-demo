# Setup
```
pipenv --python 3.8
pipenv install
pipenv run pip install 'asyncapi[http,yaml,redis,subscriber,docs]'
```

# Run worker
```
./run_worker.sh
```

# Run API docs server 
```
PYTHONPATH=. asyncapi-docs --api-module consumer_service.asyncapi_specification

curl http://127.0.0.1:5000/asyncapi.yaml
```