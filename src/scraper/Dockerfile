FROM python:3.11-bullseye

# Install system dependencies
RUN apt-get update && apt-get install --no-install-recommends --no-install-suggests -y \
    build-essential \
    libffi-dev \
    libssl-dev \
    wget \
    unzip \
    libnss3 \
    libnspr4 \
    libasound2 \
    libappindicator3-1 \
    libxss1 \
    libxtst6 \
    libx11-xcb1 \
    libgbm1 \
    libxshmfence1

# Install Google Chrome
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" | tee /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable

# Install ChromeDriver
RUN CHROME_DRIVER_VERSION=$(curl -sS chromedriver.storage.googleapis.com/LATEST_RELEASE) && \
    wget https://chromedriver.storage.googleapis.com/$CHROME_DRIVER_VERSION/chromedriver_linux64.zip \
    && unzip chromedriver_linux64.zip \
    && mv chromedriver /usr/bin/chromedriver \
    && chmod +x /usr/bin/chromedriver \
    && rm chromedriver_linux64.zip

WORKDIR /app
RUN mkdir -p /all/logs

COPY . /app

RUN pip install --no-cache-dir -r requirements.txt
RUN pip install certifi

CMD [ "python", "garage_scrapy.py" ]
