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
from ..utils import ftp_connection_info, unzip_files
from ..settings import SPRINGER_DOWNLOAD_DIR, SPRINGER_UNPACK_FOLDER, SPRINGER_WORKING_DIR

from tempfile import mkdtemp
from scrapy import Request
from scrapy.spiders import XMLFeedSpider
import pysftp


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

    def __init__(self, package_path=None, ftp_folder="/data/in", ftp_host=None, ftp_netrc=None, force=False, *args, **kwargs):
        """Construct Elsevier spider."""
        super(S3SpringerSpider, self).__init__(*args, **kwargs)
        self.ftp_folder = ftp_folder
        self.ftp_host = ftp_host
        self.ftp_netrc = ftp_netrc
        self.target_folder = SPRINGER_DOWNLOAD_DIR
        self.package_path = package_path
        self.journals = ['JHEP', 'EPJC']
        self.force = force

        # Creating target folders
        paths_of_folders = [
            os.path.join(SPRINGER_DOWNLOAD_DIR, 'EPJC'),
            os.path.join(SPRINGER_DOWNLOAD_DIR, 'JHEP'),
            os.path.join(SPRINGER_UNPACK_FOLDER, 'EPJC'),
            os.path.join(SPRINGER_UNPACK_FOLDER, 'JHEP')]

        for path_of_folder in paths_of_folders:
            if not os.path.exists(path_of_folder):
                os.makedirs(path_of_folder)

    def start_requests(self):
        """List selected folder on remote FTP and yield new zip files."""

        self.log('Harvest started.', logging.INFO)
        if self.package_path:
            self.log('Harvesting locally: %s' %
                     self.package_path, logging.INFO)
            return [Request(self.package_path, callback=self.handle_package_sftp), ]
        return self.download_files_from_sftp()

    def download_files_from_sftp(self):
        sftp_host, sftp_params = ftp_connection_info(
            self.ftp_host, self.ftp_netrc)
        cnopts = pysftp.CnOpts()
        cnopts.hostkeys = None

        self.log("Connecting to SFTP server...", logging.INFO)
        # Connect to the ftp server
        with pysftp.Connection(sftp_host, username=sftp_params['ftp_user'], password=sftp_params['ftp_password'], cnopts=cnopts) as sftp:
            self.log("SFTP connection established.", logging.INFO)

            if self.ftp_folder:
                if not sftp.isdir(self.ftp_folder):
                    self.log(
                        "Remote directory doesn't exist. Abort connection.", logging.ERROR)
                    return
                sftp.chdir(self.ftp_folder)

            # sorting packages by journals
            for journal in self.journals:
                sftp.chdir(os.path.join(self.ftp_folder, journal))
                for file in sftp.listdir():
                    if file.endswith('.zip') or file.endswith('.tar'):
                        remote_path = os.path.join(
                            self.ftp_folder, journal, file)
                        local_path = os.path.join(
                            SPRINGER_WORKING_DIR, self.target_folder, journal, file)
                        if os.path.exists(local_path) and not self.force:
                            self.log("Skipping '%s' as it is already present locally at %s." % (
                                remote_path, local_path))
                            continue

                        sftp.get(remote_path, local_path, preserve_mtime=True)
                        yield Request('file://' + local_path, callback=self.handle_package_sftp)

    def handle_package_sftp(self, response):
        """Handle the zip package and yield a request for every XML found."""
        self.log('Handling package: %s' % response.url, logging.INFO)
        package_path = response.url.replace('file://', '')
        filename = os.path.basename(response.url).rstrip(".zip")
        unzipped_files_folder = package_path.replace(SPRINGER_DOWNLOAD_DIR, SPRINGER_UNPACK_FOLDER)
        # TMP dir to extract zip packages:
        target_folder = mkdtemp(prefix=filename + "_",
                                dir=os.path.dirname(unzipped_files_folder))

        zip_filepath = response.url.replace('file://', '')

        files = unzip_files(zip_filepath, target_folder)
        self.log('Extracted files to %s' % target_folder, logging.INFO)
        # The xml files shouldn't be removed after processing; they will
        # be later uploaded to Inspire. So don't remove any tmp files here.
        for xml_file in files:
            if '.scoap' in xml_file or '.Meta' in xml_file:
                xml_url = u"file://{0}".format(os.path.abspath(xml_file))
                pdfa_name = "{0}.pdf".format(
                    os.path.basename(xml_file).split('.')[0])
                pdfa_path = os.path.join(os.path.dirname(
                    xml_file), 'BodyRef', 'PDF', pdfa_name)
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
