FROM python:3.9-alpine

ENV DIR_PATH='/parking/'

RUN mkdir -p /parking
RUN mkdir -p /parking/db
RUN pip install certifi
RUN pip install attrs
RUN pip install aiohttp
RUN pip install cffi
RUN pip install urllib3
RUN pip install pycparser
RUN pip install requests

COPY main.py /parking
COPY db.db /parking

CMD ["python3", "/parking/main.py"]