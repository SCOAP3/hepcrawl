FROM python:2.7

WORKDIR /usr/src/app

ENV PYTHONDONTWRITEBYTECODE=1
RUN mkdir /code /var/lib/scrapy /venv

copy . /code

WORKDIR /code

RUN pip install --no-cache-dir --upgrade pip==20.3.4 && \
    pip install --no-cache-dir --upgrade setuptools && \
    pip install --no-cache-dir --upgrade wheel && \
    pip install --no-cache-dir typing==3.7.4.1

RUN pip install --ignore-installed --requirement requirements.txt -e .

RUN scrapyd  & \
    sleep 10 && scrapyd-deploy
