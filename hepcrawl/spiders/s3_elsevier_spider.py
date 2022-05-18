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

from hepcrawl.extractors.s3_elsevier_parser import S3ElsevierParser
from ..settings import (
    ELSEVIER_SOURCE_DIR,
    ELSEVIER_DOWNLOAD_DIR,
    ELSEVIER_UNPACK_FOLDER
)

from scrapy import Request
from scrapy.spiders import Spider
from scrapy.selector import Selector
from scrapy.utils.python import re_rsearch
from tempfile import mkdtemp


def uncompress(filename, target_folder):
    """Unzip files (XML only) into target folder."""
    datasets = []
    if '.tar' in filename:
        with tarfile.open(filename) as archive:
            archive_name = os.path.basename(archive.name).rstrip('.tar')
            for tar_info in archive:
                if "dataset.xml" in tar_info.name:
                    datasets.append(os.path.join(target_folder, tar_info.name))
            if not os.path.exists(os.path.join(target_folder, archive_name)):
                archive.extractall(path=target_folder)
    else:
        with zipfile.ZipFile(filename) as archive:
            archive_name = os.path.basename(archive.filename).rstrip('.zip')
            for zip_info in archive.filelist:
                if "dataset.xml" in zip_info.filename:
                    datasets.append(os.path.join(target_folder, zip_info.filename))
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

    r = re.compile(r'<%(np)s[\s>].*?</%(np)s>' % {'np': nodename_patt}, re.DOTALL)
    for match in r.finditer(text):
        nodetext = header_start + match.group() + header_end
        tmp = Selector(text=nodetext, type='xml')
        tmp.remove_namespaces()
        l = tmp.xpath('//' + nodename)

        if l:
            yield l[0]


class S3ElsevierSpider(Spider):
    """Elsevier SCOPA3 crawler.

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

    name = 'Elsevier'
    start_urls = []
    itertag = ['article', 'simple-article']

    journal_mapping = {
        'PLB': 'Physics Letters B',
        'NUPHB': 'Nuclear Physics B'
    }

    ERROR_CODES = range(400, 432)

    def __init__(self, package_path=None, ftp_host='sftp', ftp_user='foo', ftp_password='pass',
                 ftp_dir='upload', ftp_port=22, force=False, *args, **kwargs):
        """Construct Elsevier spider."""
        super(S3ElsevierSpider, self).__init__(*args, **kwargs)
        self.package_path = package_path
        self.ftp_host = ftp_host
        self.ftp_user = ftp_user
        self.ftp_password = ftp_password
        self.ftp_dir = ftp_dir
        self.ftp_port = ftp_port
        self.force = force

    def start_requests(self):
        """List selected folder on locally mounted remote SFTP and yield new tar files."""
        self.log('Harvest started.', logging.INFO)

        self.create_directories()

        if self.package_path:
            # process only the package received as parameter
            self.log('Harvesting locally: %s' % self.package_path, logging.INFO)
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

        # Connect to the ftp server
        with pysftp.Connection(self.ftp_host, username=self.ftp_user, password=self.ftp_password,
                               port=self.ftp_port, cnopts=cnopts) as ftp:
            self.log("SFTP connection established.", logging.INFO)

            # change dir to remote folder.
            # if doesn't exist there's no packages in it, so exit.
            if self.ftp_dir:
                if not ftp.isdir(self.ftp_dir):
                    self.log("Remote directory doesn't exist. Abort connection.", logging.ERROR)
                    return
                ftp.chdir(self.ftp_dir)

            # download all new package files
            for remote_path in ftp.listdir():
                if not ftp.isfile(remote_path):
                    self.log("Skipping '%s' as it's not a file." % remote_path, logging.INFO)
                    continue

                if not (remote_path.endswith('.tar') or remote_path.endswith('.zip')):
                    self.log("Skipping '%s' as it doesn't end with .tar or .zip" % remote_path, logging.INFO)
                    continue

                # get local file path with filename.
                # Here path is just the filename, doesn't contain any additional path parts.
                local_file = os.path.join(ELSEVIER_DOWNLOAD_DIR, remote_path)

                if os.path.exists(local_file) and not self.force:
                    self.log("Skipping '%s' as it is already present locally at %s." % (remote_path, local_file))
                    continue

                self.log("Copy file from SFTP to %s" % local_file)

                # download file while preserving the timestamps
                ftp.get(remote_path, local_file, preserve_mtime=True)
                new_packages.append(local_file)

        return new_packages

    def handle_package(self, response):
        """Handle the package and yield a request for every XML found."""

        package_path = response.url.replace('file://', '')
        self.log('Handling package: %s' % package_path, logging.INFO)

        # extract the name of the package without extension
        filename = os.path.basename(response.url).rstrip("A.tar").rstrip('.zip')

        # create temporary directory to extract zip packages:
        target_folder = mkdtemp(prefix=filename + "_", dir=ELSEVIER_UNPACK_FOLDER)

        # uncompress files to temp directory
        files = uncompress(package_path, target_folder)

        self.log('Files uncompressed to: %s' % target_folder, logging.INFO)

        for f in files:
            if 'dataset.xml' in f:
                return self.parse_dataset(target_folder, filename, package_path, f)

    def parse_dataset(self, target_folder, filename, zip_filepath, f):
        """Parse the dataset and other xml files.
        We have one dataset.xml per package, this describes the artciles we received in this package.
        """

        self.log('Parsing dataset: %s' % f, logging.INFO)
        with open(f, 'r') as dataset_file:
            dataset = Selector(text=dataset_file.read())
            journal_data = self.parse_journal_issue(dataset, target_folder, filename)
            self.parse_journal_items(dataset, target_folder, filename, zip_filepath, journal_data)

            for i in range(len(journal_data)):
                for doi, data in journal_data[i]['articles'].items():
                    with open(data['files']['xml'], 'r') as xml_file:
                        xml_file_content = xml_file.read()
                        for nodename in self.itertag:
                            for selector in xmliter(xml_file_content, nodename):
                                yield self.parse_node(journal_data[i], selector)

    def parse_journal_issue(self, dataset, target_folder, filename):
        """Parse journal issue tags and files if there is any in the dataset.xml.
        The journal issue xmls are containing all the dois for artciles in that issue. Extract this data,
        and later update it from the journal item xml.
        """

        data = []

        for issue in dataset.xpath('//journal-issue'):
            tmp = {
                'volume': "%s %s" % (issue.xpath('//volume-issue-number/vol-first/text()')[0].extract(),
                                     issue.xpath('//volume-issue-number/suppl/text()')[0].extract()),
            }
            issue_file = os.path.join(target_folder, filename,
                                      issue.xpath('./files-info/ml/pathname/text()')[0].extract())

            self.log('Parsing journal issue xml: %s' % issue_file, logging.INFO)

            articles = {}
            with open(issue_file, 'r') as [issue_file:
                iss = Selector(text=issue_file.read())
                iss.remove_namespaces()
                for article in iss.xpath('//include-item'):
                    doi = article.xpath('./doi/text()')[0].extract()

                    first_page = None
                    if article.xpath('./pages/first-page/text()'):
                        first_page = article.xpath('./pages/first-page/text()')[0].extract()

                    last_page = None
                    if article.xpath('./pages/last-page/text()'):
                        last_page = article.xpath('./pages/last-page/text()')[0].extract()

                    articles[doi] = {'first-page': first_page,
                                     'last-page': last_page}

            tmp['articles'] = articles
            data.append(tmp)

        return data

    def parse_journal_items(self, dataset, target_folder, filename, zip_filepath, journal_data):
        """Parsing journal items, e.g. articles in the dataset.xml.
        Extends the initially collected data for the articles."""

        for x_article in dataset.xpath('//journal-item'):
            doi = x_article.xpath('./journal-item-unique-ids/doi/text()')[0].extract()

            date_xpath = './journal-item-properties/online-publication-date/text()'
            if x_article.xpath(date_xpath):
                publication_date = x_article.xpath(date_xpath)[0].extract()[:18]  # fixme magic number?
            else:
                publication_date = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")dataset.xml

            journal = x_article.xpath('./journal-item-unique-ids/jid-aid/jid/text()')[0].extract()
            journal = self.journal_mapping.get(journal, journal)

            # find the doi in journal data
            data_index = None
            for i in range(len(journal_data)):
                if doi in journal_data[i]['articles']:
                    data_index = i
                    break

            xml = os.path.join(target_folder, filename,
                               x_article.xpath('./files-info/ml/pathname/text()')[0].extract())
            pdf = os.path.join(target_folder, filename,
                               x_article.xpath('./files-info/web-pdf/pathname/text()')[0].extract())
            article_data = {
                'files':
                    {
                        'xml': xml,
                        'pdf': pdf
                    },
                'journal': journal,
                'publication-date': publication_date,
            }

            # vtex files contain every artcile of a jorunal issue
            if 'vtex' in zip_filepath:
                pdfa = os.path.join(os.path.split(pdf)[0], 'main_a-2b.pdf')
                pdfa = os.path.join(target_folder, pdfa)
                article_data['files']['pdfa'] = pdfa

            if data_index is None:
                # if this doi is not present, add a new entry
                journal_data.append({'volume': None, 'issue': None, 'articles': {doi: article_data}})
            else:
                # if it is, update the existing one
                journal_data[data_index]['articles'][doi].update(article_data)

    def parse_node(self, meta_data, node):
        self.log('Parsing node...', logging.INFO)
        parser = S3ElsevierParser()
        return parser.parse_node(meta_data, node)

    @staticmethod
    def create_directories():
        """Creates download and unpack directories in case they do not exist."""

        # create download directory if doesn't exist
        if not os.path.exists(ELSEVIER_DOWNLOAD_DIR):
            os.makedirs(ELSEVIER_DOWNLOAD_DIR)

        # create unpack directory if doesn't exist
        if not os.path.exists(ELSEVIER_UNPACK_FOLDER):
            os.makedirs(ELSEVIER_UNPACK_FOLDER)
