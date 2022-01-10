# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2017 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Spider for SCOAP3 Elsevier."""

from __future__ import absolute_import, print_function

import datetime
import logging
import os
import pysftp
import re
import tarfile
import zipfile
from tempfile import mkdtemp
import paramiko
from scrapy import Request
from scrapy.spiders import Spider
from scrapy.selector import Selector
from scrapy.utils.python import re_rsearch

from ..extractors.iop_parser import IOPParser
from ..settings import IOP_DOWNLOAD_DIR, IOP_UNPACK_FOLDER


def uncompress(filename, target_folder):
    """Unzip files (XML only) into target folder."""
    datasets = []
    if '.tar' in filename:
        with tarfile.open(filename) as archive:
            archive_name = os.path.basename(archive.name).rstrip('.tar')
            if not os.path.exists(os.path.join(target_folder, archive_name)):
                archive.extractall(path=target_folder)
    else:
        with zipfile.ZipFile(filename) as archive:
            archive_name = os.path.basename(archive.filename).rstrip('.zip')
            for zip_info in archive.filelist:
                if "dataset.xml" in zip_info.filename:
                    datasets.append(os.path.join(
                        target_folder, zip_info.filename))
            if not os.path.exists(os.path.join(target_folder, archive_name)):
                archive.extractall(path=target_folder)
    return datasets


def xmliter(text, nodename):
    """Return a iterator of Selector's over all nodes of a XML document,
       given the name of the node to iterate. Useful for parsing XML feeds.

    obj can be:
    - a Response object
    - a unicode string
    - a string encoded as utf-8
    """

    nodename_patt = re.escape(nodename)

    HEADER_START_RE = re.compile(r'^(.*?)<\s*%s(?:\s|>)' % nodename_patt, re.S)
    HEADER_END_RE = re.compile(r'<\s*/%s\s*>' % nodename_patt, re.S)

    header_start = re.search(HEADER_START_RE, text)
    header_start = header_start.group(1).strip() if header_start else ''
    header_end = re_rsearch(HEADER_END_RE, text)
    header_end = text[header_end[1]:].strip() if header_end else ''

    r = re.compile(r'<%(np)s[\s>].*?</%(np)s>' %
                   {'np': nodename_patt}, re.DOTALL)
    for match in r.finditer(text):
        nodetext = header_start + match.group() + header_end
        tmp = Selector(text=nodetext, type='xml')
        tmp.remove_namespaces()
        l = tmp.xpath('//' + nodename)

        if l:
            yield l[0]


class IOPSpider(Spider):
    """IOP SCOPA3 crawler.

    This spider can scrape either an ATOM feed (default), zip file
    or an extracted XML.

    1. Default input is the feed xml file. For every url to a zip package there
       it will yield a request to unzip them. Then for every record in
       the zip files it will yield a request to scrape them. You can also run
       this spider on a zip file or a single record file.

    2. HEPRecord will be built.


    Example usage:
    .. code-block:: console

        scrapy crawl iop -a atom_feed=file://`pwd`/tests/responses/elsevier/test_feed.xml -s "JSON_OUTPUT_DIR=tmp/"
        scrapy crawl iop -a zip_file=file://`pwd`/tests/responses/elsevier/nima.zip -s "JSON_OUTPUT_DIR=tmp/"
        scrapy crawl iop -a xml_file=file://`pwd`/tests/responses/elsevier/sample_consyn_record.xml -s "JSON_OUTPUT_DIR=tmp/"

    for logging, add -s "LOG_FILE=iop.log"

    Happy crawling!
    """

    name = 'IOP'
    start_urls = []
    itertag = ['article', 'simple-article']

    ERROR_CODES = range(400, 432)

    def __init__(self, package_path=None, ftp_host=None, ftp_user=None,
                 ftp_dir='/', ftp_port=22, *args, **kwargs):
        """Construct Elsevier spider."""
        super(IOPSpider, self).__init__(*args, **kwargs)
        self.package_path = package_path
        self.ftp_host = ftp_host
        self.ftp_user = ftp_user
        self.ftp_dir = ftp_dir
        self.ftp_port = ftp_port

    def start_requests(self):
        """List selected folder on locally mounted remote SFTP and yield new tar files."""
        self.log('Harvest started.', logging.INFO)

        self.create_directories()

        if self.package_path:
            # process only the package received as parameter
            self.log('Harvesting locally: %s' %
                     self.package_path, logging.INFO)
            yield Request(self.package_path, callback=self.handle_package)
        else:
            # if running without package path, download missing files from sftp
            new_packages = self.download_files_from_sftp()

            for new_package in new_packages:
                # add file:// prefix as it's needed for scrapy
                full_path = 'file://' + new_package

                yield Request(
                    str(full_path),
                    callback=self.handle_package
                )

    def download_files_from_sftp(self):
        """
        Downloads all files from SFTP server which doesn't exist locally.
        Returns list of newly downloaded files with their absolute local path.
        """
        new_packages = []

        # ignore remote server hostkey
        cnopts = pysftp.CnOpts()
        cnopts.hostkeys = None

        self.log("Connecting to SFTP server...", logging.INFO)
        password = os.environ.get('IOP_SFTP_PASSWORD')

        # Connect to the ftp server
        
        
        
        with pysftp.Connection(host=self.ftp_host, username=self.ftp_user, password=password) as sftp:
            print( "Connection succesfully stablished ... ")
            if self.ftp_dir:
                if not sftp.isdir(self.ftp_dir):
                    self.log("Remote directory doesn't exist. Abort connection.", logging.ERROR)
                    return
                sftp.chdir(self.ftp_dir)

            # download all new package files
            for remote_path in sftp.listdir():
                if not sftp.isfile(remote_path):
                    self.log("Skipping '%s' as it's not a file." % remote_path, logging.INFO)
                    continue

                if not (remote_path.endswith('.tar') or remote_path.endswith('.zip')):
                    self.log("Skipping '%s' as it doesn't end with .tar or .zip" % remote_path, logging.INFO)
                    continue

                # get local file path with filename.
                # Here path is just the filename, doesn't contain any additional path parts.
                local_file = os.path.join(IOP_DOWNLOAD_DIR, remote_path)

                if os.path.exists(local_file):
                    self.log("Skipping '%s' as it is already present locally at %s." % (remote_path, local_file))
                    continue

                self.log("Copy file from SFTP to %s" % local_file)

                # download file while preserving the timestamps
                sftp.get(remote_path, local_file, preserve_mtime=True)
                new_packages.append(local_file)

        return new_packages

    def handle_package(self, response):
        """Handle the package and yield a request for every XML found."""

        package_path = response.url.replace('file://', '')
        self.log('Handling package: %s' % package_path, logging.INFO)

        # extract the name of the package without extension
        filename = os.path.basename(
            response.url).rstrip("A.tar").rstrip('.zip')

        # create temporary directory to extract zip packages:
        target_folder = mkdtemp(prefix=filename + "_", dir=IOP_UNPACK_FOLDER)

        # uncompress files to temp directory
        files = uncompress(package_path, target_folder)
        self.log('Files uncompressed to: %s' % target_folder, logging.INFO)

    def parse_node(self, meta_data, node):
        self.log('Parsing node...', logging.INFO)
        parser = IOPParser()
        return parser.parse_node(meta_data, node)

    @staticmethod
    def create_directories():
        """Creates download and unpack directories in case they do not exist."""

        # create download directory if doesn't exist
        if not os.path.exists(IOP_DOWNLOAD_DIR):
            os.makedirs(IOP_DOWNLOAD_DIR)

        # create unpack directory if doesn't exist
        if not os.path.exists(IOP_UNPACK_FOLDER):
            os.makedirs(IOP_UNPACK_FOLDER)

