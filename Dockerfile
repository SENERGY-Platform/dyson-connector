FROM python:3-alpine

ARG branch
ENV BRANCH=${branch}

WORKDIR /usr/src/app

RUN apk update && apk upgrade && apk add --no-cache git gcc openssl-dev musl-dev libffi-dev

COPY requirements.txt ./
RUN pip install --no-cache-dir git+https://github.com/SENERGY-Platform/client-connector-lib.git@$BRANCH
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir cc-lib
RUN mkdir storage

CMD [ "python", "-u", "./client.py"]
