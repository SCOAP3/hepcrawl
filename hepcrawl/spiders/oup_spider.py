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

import ftputil
from ftputil.error import FTPOSError
from scrapy import Request
from scrapy.spiders import XMLFeedSpider
from time import localtime, strftime

from hepcrawl.extractors.oup_parser import OUPParser
from ..utils import ftp_connection_info, unzip_files, ftp_session_factory

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

        # if package_path is defined, don't connect to FTP server
        if self.package_path:
            self.log('Harvesting locally: %s' % self.package_path, logging.INFO)
            # return value has to be iterable
            return [Request(self.package_path, callback=self.handle_package_ftp), ]

        # connect to FTP server, yield the files to download and process
        # at the end of the process FTP will be cleaned up, all processed files will be deleted
        return self.download_files_from_ftp(self.ftp_folder)

    def delete_empty_folders(self, host, ftp_folder):
        """Delete all empty folders under 'ftp_folder'"""

        for folder_path in host.listdir(ftp_folder):
            if os.path.basename(folder_path).startswith('.'):
                self.log('Skipping hidden directory: %s' % folder_path, logging.INFO)
                continue

            if not host.listdir(folder_path):
                try:
                    host.rmdir(folder_path)
                    self.log('Deleted folder: %s' % folder_path, logging.INFO)
                except FTPOSError as e:
                    self.log('Failed to delete folder. folder_path=%s error=%s' % (folder_path, e.message), logging.ERROR)
            else:
                self.log('Skipping non-empty folder: %s' % folder_path, logging.INFO)

    def delete_downloaded_files(self, host, downloaded_files):
        """Delete all files in the 'downloaded_files' list"""
        for file_path in downloaded_files:
            host.remove(file_path)
            self.log('Deleted file: %s' % file_path, logging.INFO)

    def cleanup_ftp(self, host, ftp_folder, downloaded_files):
        """Deleting all files which has been downloaded and empty folders under 'ftp_folder'."""
        self.log('Cleaning up FTP...', logging.INFO)

        try:
            self.delete_downloaded_files(host, downloaded_files)
            self.delete_empty_folders(host, ftp_folder)
            self.log('FTP cleanup done.', logging.INFO)
        except FTPOSError as e:
            self.log('Failed to cleanup FTP! Error: %s' % e, logging.ERROR)

    def collect_files_to_download(self, host, ftp_folder):
        """
        Collects all the files in under the 'ftp_folder' folder.

        Files starting with a dot (.) are omitted.
        :param host:
        :return: list of all found file's path
        """

        collected_files = []

        for path, _, files in host.walk(ftp_folder):
            for filename in files:
                if filename.startswith('.'):
                    continue

                full_path = os.path.join(path, filename)
                if filename.endswith('.zip') or filename == 'go.xml':
                    collected_files.append(full_path)
                else:
                    self.log('File with invalid extension on FTP path=%s' % full_path, logging.WARNING)

        return collected_files

    def download_files_from_ftp(self, ftp_folder):
        """"""

        filename_prefix = strftime('%Y-%m-%d_%H:%M:%S', localtime())

        # open the FTP connection
        ftp_host, ftp_params = ftp_connection_info(self.ftp_host, self.ftp_netrc)
        with ftputil.FTPHost(ftp_host, ftp_params['ftp_user'], ftp_params['ftp_password'],
                             session_factory=ftp_session_factory) as host:

            self.log('FTP connection established.', logging.INFO)

            # find all the files it's needed to download
            files_to_download = self.collect_files_to_download(host, ftp_folder)
            for file_path in files_to_download:
                if file_path.endswith('go.xml'):
                    # skip go.xml
                    self.log('Skipping file: %s' % file_path, logging.INFO)
                    continue

                # create the filename and download the file
                self.log('Downloading file: %s' % file_path, logging.INFO)
                file_name = '%s_%s' % (filename_prefix, os.path.basename(file_path))
                local_filename = os.path.join(self.target_folder, file_name)
                host.download(file_path, local_filename)

                # yield the downloaded file
                yield Request('file://' + local_filename, callback=self.handle_package_ftp)

            # after processing the files clean up FTP
            self.cleanup_ftp(host, ftp_folder, files_to_download)

    def handle_package_ftp(self, response):
        """Handle a zip package and yield every XML found."""

        # remove local schema from path
        zip_filepath = response.url.replace('file://', '')

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
