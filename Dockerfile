FROM python:2.7

WORKDIR /usr/src/app

ENV PYTHONDONTWRITEBYTECODE=1
RUN mkdir /code /var/lib/scrapy /venv

copy . /code

WORKDIR /code

RUN pip install --no-cache-dir --upgrade pip==20.3.4 && \
    pip install --no-cache-dir --upgrade setuptools && \
    pip install --no-cache-dir --upgrade wheel

RUN pip install --no-cache-dir -r requirements.txt -e .

RUN scrapyd  & \
    sleep 10 && scrapyd-deploy
