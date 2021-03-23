FROM app_accounting_service_worker:latest

### Install NodeJS begin
ENV NODE_VERSION=12.6.0
RUN apt-get update
RUN apt-get install -y curl
RUN curl -o- https://raw.githubusercontent.com/creationix/nvm/v0.34.0/install.sh | bash
ENV NVM_DIR=/root/.nvm
RUN . "$NVM_DIR/nvm.sh" && nvm install ${NODE_VERSION}
RUN . "$NVM_DIR/nvm.sh" && nvm use v${NODE_VERSION}
RUN . "$NVM_DIR/nvm.sh" && nvm alias default v${NODE_VERSION}
ENV PATH="/root/.nvm/versions/node/v${NODE_VERSION}/bin/:${PATH}"
RUN node --version
RUN npm --version
### Install NodeJS end

# need to install git to make "ag" command work
RUN apt-get install -y git

RUN npm install -g @asyncapi/generator
RUN npm install -g http-server

# generate spec fo file
RUN pip install pyyaml
RUN PYTHONPATH=. python accounting_service/asyncapi_specification.py > asyncapi.yaml

# generate HTML
RUN ag asyncapi.yaml @asyncapi/html-template -o ./asyncapi_html

# run server
CMD ["http-server /code/asyncapi_html"]