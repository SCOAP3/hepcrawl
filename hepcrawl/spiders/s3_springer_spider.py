# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2016 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Spider for SCOAP3 Springer."""

from __future__ import absolute_import, print_function

import logging
import os

from hepcrawl.extractors.s3_springer_parser import S3SpringerParser
from ..utils import ftp_list_files, ftp_connection_info, unzip_files
from ..settings import SPRINGER_DOWNLOAD_DIR, SPRINGER_UNPACK_FOLDER

from tempfile import mkdtemp
from scrapy import Request
from scrapy.spiders import XMLFeedSpider


class S3SpringerSpider(XMLFeedSpider):
    """Springer SCOPA3 crawler.

    This spider can scrape either an ATOM feed (default), zip file
    or an extracted XML.

    1. Default input is the feed xml file. For every url to a zip package there
       it will yield a request to unzip them. Then for every record in
       the zip files it will yield a request to scrape them. You can also run
       this spider on a zip file or a single record file.

    2. If needed, it will try to scrape Sciencedirect web page.

    3. HEPRecord will be built.


    Example usage:
    .. code-block:: console

        scrapy crawl elsevier -a atom_feed=file://`pwd`/tests/responses/elsevier/test_feed.xml -s "JSON_OUTPUT_DIR=tmp/"
        scrapy crawl elsevier -a zip_file=file://`pwd`/tests/responses/elsevier/nima.zip -s "JSON_OUTPUT_DIR=tmp/"
        scrapy crawl elsevier -a xml_file=file://`pwd`/tests/responses/elsevier/sample_consyn_record.xml -s "JSON_OUTPUT_DIR=tmp/"

    for logging, add -s "LOG_FILE=elsevier.log"

    * This is useful: https://www.elsevier.com/__data/assets/pdf_file/0006/58407/ja50_tagbytag5.pdf

    Happy crawling!
    """

    name = 'Springer'
    start_urls = []
    iterator = 'iternodes'
    itertag = 'Publisher'

    ERROR_CODES = range(400, 432)

    def __init__(self, package_path=None, ftp_folder="data/in", ftp_host=None, ftp_netrc=None, *args, **kwargs):
        """Construct Elsevier spider."""
        super(S3SpringerSpider, self).__init__(*args, **kwargs)
        self.ftp_folder = ftp_folder
        self.ftp_host = ftp_host
        self.ftp_netrc = ftp_netrc
        self.target_folder = SPRINGER_DOWNLOAD_DIR
        self.package_path = package_path
        if not os.path.exists(self.target_folder):
            os.makedirs(self.target_folder)

    def start_requests(self):
        """List selected folder on remote FTP and yield new zip files."""
        if self.package_path:
            ftp_params = {"ftp_local_filename": self.package_path}
            yield Request(self.package_path, meta=ftp_params, callback=self.handle_package_ftp)
        else:
            ftp_host, ftp_params = ftp_connection_info(self.ftp_host, self.ftp_netrc)
            missing_files = []
            for journal in ['EPJC', 'JHEP']:
                _, tmp_missing_files = ftp_list_files(
                    os.path.join(self.ftp_folder, journal),
                    os.path.join(self.target_folder, journal),
                    server=ftp_host,
                    user=ftp_params['ftp_user'],
                    password=ftp_params['ftp_password']
                )
                missing_files.extend(tmp_missing_files)
            # TODO - add checking if the package was already downloaded

            for remote_file in missing_files:
                journal = 'EPJC' if 'EPJC' in remote_file else 'JHEP'
                remote_file = str(remote_file).strip('/data/in/%s/' % journal)
                ftp_params["ftp_local_filename"] = os.path.join(
                    self.target_folder,
                    journal,
                    remote_file
                )
                remote_url = "ftp://{0}/{1}".format(ftp_host, os.path.join('data/in/', journal, remote_file))
                yield Request(
                    str(remote_url),
                    meta=ftp_params,
                    callback=self.handle_package_ftp)

    def handle_package_ftp(self, response):
        """Handle the zip package and yield a request for every XML found."""
        self.log('Handling package: %s' % response.url, logging.INFO)

        filename = os.path.basename(response.url).rstrip(".zip")

        # TMP dir to extract zip packages:
        target_folder = mkdtemp(prefix=filename + "_", dir=SPRINGER_UNPACK_FOLDER)

        zip_filepath = response.meta["ftp_local_filename"]
        if zip_filepath.startswith('file://'):
            zip_filepath = zip_filepath[7:]

        files = unzip_files(zip_filepath, target_folder)
        self.log('Extracted files to %s' % target_folder, logging.INFO)
        # The xml files shouldn't be removed after processing; they will
        # be later uploaded to Inspire. So don't remove any tmp files here.
        for xml_file in files:
            if '.scoap' in xml_file or '.Meta' in xml_file:
                xml_url = u"file://{0}".format(os.path.abspath(xml_file))
                pdfa_name = "{0}.pdf".format(os.path.basename(xml_file).split('.')[0])
                pdfa_path = os.path.join(os.path.dirname(xml_file), 'BodyRef', 'PDF', pdfa_name)
                pdfa_url = u"file://{0}".format(pdfa_path)
                yield Request(
                    xml_url,
                    meta={"package_path": zip_filepath,
                          "xml_url": xml_url,
                          "pdfa_url": pdfa_url},
                )

    def parse_node(self, response, node):
        self.log('Parsing node...', logging.INFO)
        parser = S3SpringerParser()
        return parser.parse_node(response, node)
