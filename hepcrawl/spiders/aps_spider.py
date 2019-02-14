# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2015, 2016 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Spider for APS."""

from __future__ import absolute_import, print_function

import json

from datetime import datetime
from errno import EEXIST as FILE_EXISTS, ENOENT as NO_SUCH_FILE_OR_DIR
from furl import furl
from os import path, makedirs
from scrapy import Request, Spider

from hepcrawl.extractors.aps_parser import APSParser
from ..settings import LAST_RUNS_PATH


class APSSpider(Spider):
    """APS crawler.

    Uses the APS REST API v2. See documentation here:
    http://harvest.aps.org/docs/harvest-api#endpoints

    scrapy crawl APS -a 'from_date=2016-05-01' -a 'until_date=2016-05-15' -a 'sets=openaccess'
    """
    name = 'APS'
    aps_base_url = "http://harvest.aps.org/v2/journals/articles"

    def __init__(self, url=None, from_date=None, until_date=None, date="published", journals=None,
                 sets=None, per_page=100, **kwargs):
        """Construct APS spider."""
        super(APSSpider, self).__init__(**kwargs)
        if url is None:
            # We Construct.
            self.params = {}
            if from_date:
                self.params['from'] = from_date
            else:
                last_run = self._load_last_run()
                if last_run:
                    f = last_run['last_run_finished_at'].split('T')[0]
                    self.params['from'] = f
            if until_date:
                self.params['until'] = until_date
            if date:
                self.params['date'] = date
            if journals:
                self.params['journals'] = journals
            if per_page:
                self.params['per_page'] = per_page
            if sets:
                self.params['set'] = sets

            # Put it together: furl is awesome
            url = furl(APSSpider.aps_base_url).add(self.params).url
        self.url = url

    def start_requests(self):
        """Just yield the url."""
        started_at = datetime.utcnow()

        yield Request(self.url)

        self._save_run(started_at)

    def _last_run_file_path(self):
        """Render a path to a file where last run information is stored.
        Returns:
            string: path to last runs path
        """
        lasts_run_path = LAST_RUNS_PATH
        file_name = 'test.json'
        return path.join(lasts_run_path, self.name, file_name)

    def _load_last_run(self):
        """Return stored last run information
        Returns:
            Optional[dict]: last run information or None if don't exist
        """
        file_path = self._last_run_file_path()
        try:
            with open(file_path) as f:
                last_run = json.load(f)
                return last_run
        except IOError as exc:
            if exc.errno == NO_SUCH_FILE_OR_DIR:
                return None
            raise

    def _save_run(self, started_at):
        """Store last run information
        Args:
            started_at (datetime.datetime)
        Raises:
            IOError: if writing the file is unsuccessful
        """
        last_run_info = {
            'spider': self.name,
            'set': self.params['set'],
            'from': self.params.get('from', None),
            'until': self.params.get('until', None),
            'date': self.params['date'],
            'journals': self.params.get('journals', None),
            'per_page': self.params['per_page'],
            'last_run_started_at': started_at.isoformat(),
            'last_run_finished_at': datetime.utcnow().isoformat(),
        }

        file_path = self._last_run_file_path()

        try:
            makedirs(path.dirname(file_path))
        except OSError as exc:
            if exc.errno != FILE_EXISTS:
                raise

        with open(file_path, 'w') as f:
            json.dump(last_run_info, f, indent=4)

    def parse(self, response):
        parser = APSParser()
        return parser.parse(response)
