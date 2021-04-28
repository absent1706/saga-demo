#### Important!
##### Due to having common folder (app_common), make sure docker build context is one folder HIGHER than current one

# set base image (host OS)
FROM python:3.8-slim
RUN pip3 install pipenv

# set the working directory in the container
WORKDIR /code

# copy the dependencies file to the working directory
COPY ./order_service/Pipfile* ./

# install dependencies
RUN pipenv install --dev --system --deploy --ignore-pipfile
RUN pip install 'asyncapi[http,yaml,redis,subscriber,docs]'
COPY ./saga_framework-0.1-py3-none-any.whl ./
RUN pip install saga_framework-0.1-py3-none-any.whl

# copy the content of the local src directory to the working directory
COPY ./order_service/run_worker.sh .
COPY ./order_service/order_service order_service
COPY ./app_common order_service/app_common

# command to run on container start
ENV PYTHONPATH=.
ENV FLASK_APP=order_service/app.py
CMD ["flask", "run"]