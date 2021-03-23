#### Important!
##### Due to having common folder (app_common), make sure docker build context is one folder HIGHER than current one

# set base image (host OS)
FROM python:3.8-slim
RUN pip3 install pipenv

# set the working directory in the container
WORKDIR /code

# copy the dependencies file to the working directory
COPY ./consumer_service/Pipfile* ./

# install dependencies
RUN pipenv install --dev --system --deploy --ignore-pipfile
RUN pip install 'asyncapi[http,yaml,redis,subscriber,docs]'

# copy the content of the local src directory to the working directory
COPY ./consumer_service/consumer_service consumer_service
COPY ./app_common consumer_service/app_common

# command to run on container start
ENV PYTHONPATH=.
CMD ["celery", "-A", "consumer_service.worker", "worker", "--loglevel=INFO"]