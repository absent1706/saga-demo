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
PYTHONPATH=. pipenv run asyncapi-docs --api-module restaurant_service.asyncapi_specification

curl http://127.0.0.1:5000/asyncapi.yaml
```