FROM python:3.11-bullseye

RUN apt-get update && apt-get install --no-install-recommends --no-install-suggests -y \
    build-essential \
    libffi-dev \
    libssl-dev

WORKDIR /app

COPY ../.. /app

RUN pip install --no-cache-dir -r requirements.txt
RUN pip install certifi

CMD [ "python", "garage_scrapy.py" ]