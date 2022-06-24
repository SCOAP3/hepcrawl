# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2015, 2016 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Pipelines for saving extracted items are defined here.

Don't forget to add pipelines to the ITEM_PIPELINES setting
See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html
"""

import os
import datetime
import json
import requests

import logstash
import logging
import structlog

from .utils import get_temporary_file


LOG_STASH_HOST = os.environ.get('LOG_STASH_HOST', 'localhost')
LOG_STASH_PORT = os.environ.get('LOG_STASH_PORT', '5959')
LOG_STASH_VERSION = os.environ.get('LOG_STASH_VERSION', 1)
LOGGER = logging.getLogger('python-logstash-logger')
LOGGER.setLevel(logging.INFO)
LOGGER.addHandler(logstash.LogstashHandler(LOG_STASH_HOST, LOG_STASH_PORT, version=LOG_STASH_VERSION))


def has_publication_info(item):
    """If any publication info."""
    return item.get('pubinfo_freetext') or item.get('journal_volume') or \
        item.get('journal_title') or \
        item.get('journal_year') or \
        item.get('journal_issue') or \
        item.get('journal_fpage') or \
        item.get('journal_lpage') or \
        item.get('journal_artid') or \
        item.get('journal_doctype')


def filter_fields(item, keys):
    """Filter away keys."""
    for key in keys:
        item.pop(key, None)


class JsonWriterPipeline(object):
    """Pipeline for outputting items in JSON lines format."""

    def __init__(self, output_uri=None):
        self.output_uri = output_uri
        self.count = 0

    @classmethod
    def from_crawler(cls, crawler):
        if crawler.spider is not None:
            prefix = "{0}_".format(crawler.spider.name)
        else:
            prefix = "hepcrawl"

        output_uri = get_temporary_file(
            prefix=prefix,
            suffix=".json",
            directory=crawler.settings.get("JSON_OUTPUT_DIR")
        )
        return cls(
            output_uri=output_uri,
        )

    def open_spider(self, spider):
        self.file = open(self.output_uri, "wb")
        self.file.write("[")

    def close_spider(self, spider):
        self.file.write("]\n")
        self.file.close()
        spider.logger.info("Wrote {0} records to {1}".format(
            self.count,
            self.output_uri,
        ))

    def process_item(self, item, spider):
        line = ""
        if self.count > 0:
            line = "\n,"
        line += json.dumps(dict(item), indent=4)
        self.file.write(line)
        self.count += 1
        return item


class InspireAPIPushPipeline(object):
    """Push to INSPIRE API via tasks API."""

    def __init__(self):
        self.count = 0
        self.dois = []
        self.logger = structlog.getLogger()

    def process_item(self, item, spider):
        """Convert internal format to INSPIRE data model."""
        self.count += 1

        if 'dois' in item:
            value = [doi['value'] for doi in item['dois']]
            if len(value) > 0:
                doi = str(value[0])
                self.logger.info('Processing article.', name=spider.name, doi=str(doi))
                self.dois.append(doi)
            else:
                self.logger.error('Empty DOIs for this article.', name=spider.name)
        else:
            self.logger.error('Cannot find DOIs for the parsed articles.', name=spider.name)

        if 'related_article_doi' in item:
            item['dois'] += item.pop('related_article_doi', [])

        source = item.pop('source', spider.name)

        # parse imported records from repo.scoap3.org and manual input
        cr_date = datetime.datetime.now().isoformat()
        method = source
        acquisition_source_method = source

        item['acquisition_source'] = {
            'source': source,
            # NOTE: Keeps method same as source to conform with INSPIRE
            # submissions which add `submissions` to this field.
            'method': acquisition_source_method,
            'date': cr_date,
            'submission_number': os.environ.get('SCRAPY_JOB', ''),
        }

        if 'record_creation_date' not in item:
            item['record_creation_date'] = datetime.datetime.now().isoformat()

        item['titles'] = [{
            'title': item.pop('title', ''),
            'subtitle': item.pop('subtitle', ''),
            'source': source,
        }]

        item['abstracts'] = [{
            'value': item.pop('abstract', ''),
            'source': source,
        }]

        publication_date = item.pop('date_published', '')
        if publication_date:
            # fixing broken date format
            tmp_split = publication_date.split('-')
            if(len(tmp_split) == 3):
                pass
            elif(len(tmp_split) == 2):
                tmp_split.append("1")
            else:
                tmp_split.append("1").append("1")
            tmp_date = datetime.date(int(tmp_split[0]),
                                     int(tmp_split[1]),
                                     int(tmp_split[2]))
            publication_date = tmp_date.strftime('%Y-%m-%d')

        item['imprints'] = [{
                            'date': publication_date,
                            'publisher': source,
                            }]

        item['copyright'] = [{
            'holder': item.pop('copyright_holder', ''),
            'year': item.pop('copyright_year', ''),
            'statement': item.pop('copyright_statement', ''),
            'material': item.pop('copyright_material', ''),
        }]
        if not item.get('publication_info'):
            if has_publication_info(item):
                item['publication_info'] = [{
                    'journal_title': item.pop('journal_title', ''),
                    'journal_volume': item.pop('journal_volume', ''),
                    'year': int(item.pop('journal_year', 0)) or '',
                    'journal_issue': item.pop('journal_issue', ''),
                    'artid': item.pop('journal_artid', ''),
                    'page_start': item.pop('journal_fpage', ''),
                    'page_end': item.pop('journal_lpage', ''),
                    'material': item.pop('journal_doctype', ''),
                    'pubinfo_freetext': item.pop('pubinfo_freetext', ''),
                }]

        # Remove any fields
        filter_fields(item, [
            'journal_title',
            'journal_volume',
            'journal_year',
            'journal_issue',
            'journal_fpage',
            'journal_lpage',
            'journal_doctype',
            'journal_artid',
            'pubinfo_freetext',
        ])

        return item

    def _prepare_payload(self, spider):
        """Return payload for push."""
        payload = dict(
            job_id=os.environ['SCRAPY_JOB'],
            results_uri=os.environ['SCRAPY_FEED_URI'],
            log_file=os.environ['SCRAPY_LOG_FILE'],
        )
        try:
            payload['errors'] = [
                (str(err['exception']), str(err['sender']))
                for err in spider.state.get('errors', [])
            ]
        except Exception as e:
            spider.logger.error("Cannot add errors.")
            payload['errors'] = [
                (str(e), 'pipeline')
            ]
        return payload

    def _cleanup(self, spider):
        """Run cleanup."""
        # Cleanup errors
        try:
            if 'errors' in spider.state:
                del spider.state['errors']
        except Exception:
            spider.logger.error("Cannot cleanup errors.")

    def close_spider(self, spider):
        """Post results to HTTP API."""
        task_endpoint = spider.settings['API_PIPELINE_TASK_ENDPOINT_MAPPING'].get(
            spider.name, spider.settings['API_PIPELINE_TASK_ENDPOINT_DEFAULT']
        )
        api_url = os.path.join(
            spider.settings['API_PIPELINE_URL'],
            task_endpoint
        )
        if api_url and 'SCRAPY_JOB' in os.environ:
            requests.post(api_url, json={
                "kwargs": self._prepare_payload(spider)
            })
            self.logger.info('Spider successfully send payload.', name=spider.name, dois=self.dois, count=self.count)
        else:
            self.logger.error('Spider cannot send payload.', name=spider.name, dois=self.dois, count=self.count)
        self._cleanup(spider)


class InspireCeleryPushPipeline(InspireAPIPushPipeline):
    """Push to INSPIRE API via Celery."""

    def __init__(self):
        from celery import Celery

        super(InspireCeleryPushPipeline, self).__init__()
        self.celery = Celery()

    def open_spider(self, spider):
        self.celery.conf.update(dict(
            BROKER_URL=spider.settings['BROKER_URL'],
            CELERY_RESULT_BACKEND=spider.settings['CELERY_RESULT_BACKEND'],
            CELERY_ACCEPT_CONTENT=spider.settings['CELERY_ACCEPT_CONTENT'],
            CELERY_TIMEZONE=spider.settings['CELERY_TIMEZONE'],
            CELERY_DISABLE_RATE_LIMITS=spider.settings['CELERY_DISABLE_RATE_LIMITS'],
            CELERY_TASK_SERIALIZER='json',
            CELERY_RESULT_SERIALIZER='json',
        ))

    def close_spider(self, spider):
        """Post results to BROKER API."""
        if 'SCRAPY_JOB' in os.environ:
            task_endpoint = spider.settings['API_PIPELINE_TASK_ENDPOINT_MAPPING'].get(
                spider.name, spider.settings['API_PIPELINE_TASK_ENDPOINT_DEFAULT']
            )
            self.celery.send_task(
                task_endpoint,
                kwargs=self._prepare_payload(spider),
            )
            LOGGER.info('The spider successfully send payload.', extra=dict(
                name=spider.name, dois=self.dois, count=self.count
            ))
            self.logger.info('Spider successfully send payload.', name=spider.name, dois=self.dois, count=self.count)
        else:
            LOGGER.info('The spider successfully send payload.', extra=dict(
               name=spider.name, dois=self.dois, count=self.count
            ))
            self.logger.error('Spider cannot send payload.', name=spider.name, dois=self.dois, count=self.count)
        self._cleanup(spider)
