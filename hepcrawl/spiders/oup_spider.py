# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2015, 2016 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Spider for Oxford University Press."""

from __future__ import absolute_import, print_function

import logging
import os

from scrapy import Request
from scrapy.spiders import XMLFeedSpider
from time import localtime, strftime

from hepcrawl.extractors.oup_parser import OUPParser
from ..utils import (
    ftp_list_files,
    ftp_connection_info,
    unzip_files, ftp_list_folders)

from ..settings import OXFORD_DOWNLOAD_DIR


class OxfordUniversityPressSpider(XMLFeedSpider):
    """Oxford University Press SCOAP3 crawler.

    This spider connects to a given FTP hosts and downloads zip files with
    XML files for extraction into HEP records.

    This means that it generates the URLs for Scrapy to crawl in a special way:

    1. First it connects to a FTP host and lists all the new ZIP files found
       on the remote server and downloads them to a designated local folder,
       using `start_requests()`.

    2. Then the ZIP file is unpacked and it lists all the XML files found
       inside, via `handle_package()`. Note the callback from `start_requests()`

    3. Finally, now each XML file is parsed via `parse_node()`.

    To run a crawl, you need to pass FTP connection information via
    `ftp_host` and `ftp_netrc`:``

    .. code-block:: console

        scrapy crawl OUP -a 'ftp_host=ftp.example.com' -a 'ftp_netrc=/path/to/netrc'


    Happy crawling!
    """

    name = 'OUP'
    custom_settings = {}
    start_urls = []
    iterator = 'html'  # this fixes a problem with parsing the record
    itertag = 'article'

    def __init__(self, package_path=None, ftp_folder="hooks", ftp_host=None, ftp_netrc=None, *args, **kwargs):
        """Construct OUP spider."""
        super(OxfordUniversityPressSpider, self).__init__(*args, **kwargs)
        self.ftp_folder = ftp_folder
        self.ftp_host = ftp_host
        self.ftp_netrc = ftp_netrc
        self.target_folder = OXFORD_DOWNLOAD_DIR
        self.package_path = package_path
        if not os.path.exists(self.target_folder):
            os.makedirs(self.target_folder)

    def start_requests(self):
        """List selected folder on remote FTP and yield new zip files."""

        self.log('Harvest started.', logging.INFO)

        if self.package_path:
            # local package handling.
            self.log('Harvesting locally: %s' % self.package_path, logging.INFO)
            yield Request(self.package_path, callback=self.handle_package_ftp, meta={'local': True})
        else:
            # connect to ftp and download files
            ftp_host, ftp_params = ftp_connection_info(self.ftp_host, self.ftp_netrc)
            for folder in ftp_list_folders(
                self.ftp_folder,
                server=ftp_host,
                user=ftp_params['ftp_user'],
                password=ftp_params['ftp_password']
            ):
                new_download_name = strftime('%Y-%m-%d_%H:%M:%S', localtime())
                new_files, _ = ftp_list_files(
                    os.path.join(self.ftp_folder, folder),
                    self.target_folder,
                    server=ftp_host,
                    user=ftp_params['ftp_user'],
                    password=ftp_params['ftp_password']
                )

                self.log('New files on FTP: %s' % new_files, logging.INFO)
                for remote_file in new_files:
                    self.log('Processing file: %s' % remote_file, logging.INFO)
                    # Cast to byte-string for scrapy compatibility
                    remote_file = str(remote_file)
                    if '.zip' in remote_file:
                        ftp_params["ftp_local_filename"] = os.path.join(
                            self.target_folder, "_".join([new_download_name, os.path.basename(remote_file)])
                        )
                        remote_url = "ftp://{0}/{1}".format(ftp_host, remote_file)
                        yield Request(
                            str(remote_url),
                            meta=ftp_params,
                            callback=self.handle_package_ftp
                        )

    def handle_package_ftp(self, response):
        """Handle a zip package and yield every XML found."""
        if 'local' in response.meta:
            # add local package name without 'file://'
            zip_filepath = response.url.replace('file://', '')
        else:
            zip_filepath = response.body

        self.log('Processing ftp package: %s' % zip_filepath, logging.INFO)

        zip_target_folder = zip_filepath
        while True:
            zip_target_folder, ext = os.path.splitext(zip_target_folder)
            if ext == '':
                break

        # extract pdf files
        if ".pdf" in zip_filepath:
            self.log('Unzipping pdf...', logging.INFO)
            zip_target_folder = os.path.join(zip_target_folder, "pdf")
            unzip_files(zip_filepath, zip_target_folder, ".pdf")

        if zip_target_folder.endswith("_archival"):
            self.log('Unzipping archival...', logging.INFO)
            zip_target_folder = zip_target_folder[0:zip_target_folder.find("_archival")]
            zip_target_folder = os.path.join(zip_target_folder, "archival")
            unzip_files(zip_filepath, zip_target_folder, ".pdf")

        # extract and yield xml file for parsing
        if ".xml" in zip_filepath:
            self.log('Unzipping and parsing xml...', logging.INFO)
            xml_files = unzip_files(zip_filepath, zip_target_folder, '.xml')
            for xml_file in xml_files:
                dir_path = os.path.dirname(xml_file)
                filename = os.path.basename(xml_file).split('.')[0]
                pdf_url = os.path.join(dir_path, "pdf", "%s.%s" % (filename, 'pdf'))
                pdfa_url = os.path.join(dir_path, "archival", "%s.%s" % (filename, 'pdf'))
                yield Request(
                    "file://{0}".format(xml_file),
                    meta={"package_path": zip_filepath,
                          "xml_url": xml_file,
                          "pdf_url": pdf_url,
                          "pdfa_url": pdfa_url}
                )

    def parse_node(self, response, node):
        self.log('Parsing node...', logging.INFO)
        parser = OUPParser()
        return parser.parse_node(response, node)
