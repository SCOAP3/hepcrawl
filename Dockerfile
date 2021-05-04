FROM python:3

WORKDIR /usr/src/app

ENV PYTHONDONTWRITEBYTECODE=1
RUN mkdir /code /var/lib/scrapy /venv

copy . /code

ENV PATH="/home/test/.local/bin:${PATH}"

WORKDIR /code
RUN pip install --no-cache-dir -e .
