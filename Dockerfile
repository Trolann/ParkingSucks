FROM python:3.11-alpine

RUN apk update && apk add --no-cache \
    build-base \
    libffi-dev \
    openssl-dev

WORKDIR /app

COPY . /app

RUN pip install --no-cache-dir -r requirements.txt

CMD [ "python", "garage_scrapy.py" ]
