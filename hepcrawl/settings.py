# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2015, 2016 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Scrapy settings for HEPcrawl project.

For simplicity, this file contains only settings considered important or
commonly used. You can find more settings consulting the documentation:

http://doc.scrapy.org/en/latest/topics/settings.html
http://scrapy.readthedocs.org/en/latest/topics/downloader-middleware.html
http://scrapy.readthedocs.org/en/latest/topics/spider-middleware.html
"""

import os


BOT_NAME = 'hepcrawl'

SPIDER_MODULES = ['hepcrawl.spiders']
NEWSPIDER_MODULE = 'hepcrawl.spiders'

# Crawl responsibly by identifying yourself (and your website) on the
# user-agent
USER_AGENT = 'hepcrawl (+http://www.inspirehep.net)'

# Allow duplicate requests
DUPEFILTER_CLASS = "scrapy.dupefilters.BaseDupeFilter"

# Configure maximum concurrent requests performed by Scrapy (default: 16)
# CONCURRENT_REQUESTS=32

# Configure a delay for requests for the same website (default: 0)
# See
# http://scrapy.readthedocs.org/en/latest/topics/settings.html#download-delay
# See also autothrottle settings and docs
# DOWNLOAD_DELAY=3
# The download delay setting will honor only one of:
# CONCURRENT_REQUESTS_PER_DOMAIN=16
# CONCURRENT_REQUESTS_PER_IP=16

# Disable cookies (enabled by default)
# COOKIES_ENABLED=False

# Disable Telnet Console (enabled by default)
# TELNETCONSOLE_ENABLED=False

# Override the default request headers:
# DEFAULT_REQUEST_HEADERS = {
#  'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
#  'Accept-Language': 'en',
# }

# Enable or disable spider middlewares
# See http://scrapy.readthedocs.org/en/latest/topics/spider-middleware.html
SPIDER_MIDDLEWARES = {
    'hepcrawl.middlewares.ErrorHandlingMiddleware': 543,
}

# Enable or disable downloader middlewares
# See http://scrapy.readthedocs.org/en/latest/topics/downloader-middleware.html
DOWNLOADER_MIDDLEWARES = {
    'hepcrawl.middlewares.ErrorHandlingMiddleware': 543,
}

# Enable or disable extensions
# See http://scrapy.readthedocs.org/en/latest/topics/extensions.html
EXTENSIONS = {
    'hepcrawl.extensions.ErrorHandler': 555,
}
SENTRY_DSN = os.environ.get('APP_SENTRY_DSN')
if SENTRY_DSN:
    EXTENSIONS['scrapy_sentry.extensions.Errors'] = 10

# Configure item pipelines
# See http://scrapy.readthedocs.org/en/latest/topics/item-pipeline.html
ITEM_PIPELINES = {
    # 'hepcrawl.pipelines.JsonWriterPipeline': 300,
    'scrapy.pipelines.files.FilesPipeline': 1,
    'hepcrawl.pipelines.InspireCeleryPushPipeline': 300,
}

# Files Pipeline settings
# =======================
FILES_STORE = os.environ.get(
    "APP_FILES_STORE",
    'files'
)
FILES_URLS_FIELD = 'file_urls'
FILES_RESULT_FIELD = 'files'

# INSPIRE Push Pipeline settings
# ==============================
API_PIPELINE_URL = "http://localhost:5555/api/task/async-apply"
API_PIPELINE_TASK_ENDPOINT_DEFAULT = "inspire_crawler.tasks.submit_results"
API_PIPELINE_TASK_ENDPOINT_MAPPING = {}   # e.g. {'my_spider': 'special.task'}

# Celery
# ======
BROKER_URL = os.environ.get(
    "APP_BROKER_URL",
    "amqp://scoap3:RABBITMQPASS@scoap3-mq1.cern.ch:5672/scoap3")
CELERY_RESULT_BACKEND = os.environ.get(
    "APP_CELERY_RESULT_BACKEND",
    "redis://:mypass@scoap3-cache1.cern.ch:6379/1")
CELERY_ACCEPT_CONTENT = ['json', 'msgpack', 'yaml']
CELERY_TIMEZONE = 'Europe/Amsterdam'
CELERY_DISABLE_RATE_LIMITS = True

# Jobs
# ====
JOBDIR = "jobs"

# these directory configs will be overwritten in production configuration
BASE_WORKING_DIR = os.environ.get(
    'HEPCRAWL_BASE_WORKING_DIR',
    '/virtualenv/data/'
)

ELSEVIER_WORKING_DIR = os.path.join(BASE_WORKING_DIR, "Elsevier")
ELSEVIER_SOURCE_DIR = "/mnt/elsevier-sftp"
ELSEVIER_DOWNLOAD_DIR = os.path.join(ELSEVIER_WORKING_DIR, "download")
ELSEVIER_UNPACK_FOLDER = os.path.join(ELSEVIER_WORKING_DIR, "unpacked")

OXFORD_WORKING_DIR = os.path.join(BASE_WORKING_DIR, "OUP")
OXFORD_DOWNLOAD_DIR = os.path.join(OXFORD_WORKING_DIR, "download")
OXFORD_UNPACK_FOLDER = os.path.join(OXFORD_WORKING_DIR, "unpacked")

SPRINGER_WORKING_DIR = os.path.join(BASE_WORKING_DIR, "Springer")
SPRINGER_DOWNLOAD_DIR = os.path.join(SPRINGER_WORKING_DIR, "download")
SPRINGER_UNPACK_FOLDER = os.path.join(SPRINGER_WORKING_DIR, "unpacked")

IOP_SOURCE_DIR = ""
IOP_WORKING_DIR = os.path.join(BASE_WORKING_DIR, "IOP")
IOP_DOWNLOAD_DIR = os.path.join(SPRINGER_WORKING_DIR, "download")
IOP_UNPACK_FOLDER = os.path.join(SPRINGER_WORKING_DIR, "unpacked")

# Location of last run information
LAST_RUNS_PATH = os.environ.get(
    'APP_LAST_RUNS_PATH',
    '/eos/project/s/scoap3repo/last_run'
)


# Enable and configure the AutoThrottle extension (disabled by default)
# See http://doc.scrapy.org/en/latest/topics/autothrottle.html
# NOTE: AutoThrottle will honour the standard settings for concurrency and delay
# AUTOTHROTTLE_ENABLED=True
# The initial download delay
# AUTOTHROTTLE_START_DELAY=5
# The maximum download delay to be set in case of high latencies
# AUTOTHROTTLE_MAX_DELAY=60
# Enable showing throttling stats for every response received:
# AUTOTHROTTLE_DEBUG=False

# Enable and configure HTTP caching (disabled by default)
# See http://scrapy.readthedocs.org/en/latest/topics/downloader-middleware.html#httpcache-middleware-settings
# HTTPCACHE_ENABLED=True
# HTTPCACHE_EXPIRATION_SECS=0
# HTTPCACHE_DIR='httpcache'
# HTTPCACHE_IGNORE_HTTP_CODES=[]
# HTTPCACHE_STORAGE='scrapy.extensions.httpcache.FilesystemCacheStorage'

try:
    from local_settings import *
except ImportError:
    pass

