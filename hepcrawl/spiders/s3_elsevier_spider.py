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
import os
import re
import tarfile
import zipfile

from ..items import HEPRecord
from ..loaders import HEPLoader
from ..settings import (
    ELSEVIER_SOURCE_DIR,
    ELSEVIER_DOWNLOAD_DIR,
    ELSEVIER_UNPACK_FOLDER
)
from ..utils import get_license

from scrapy import Request
from scrapy.spiders import XMLFeedSpider
from scrapy.selector import Selector
from scrapy.utils.python import re_rsearch
from tempfile import mkdtemp


def list_files(path, target_folder):
    files = os.listdir(path)
    missing_files = []
    all_files = []
    for filename in files:
        destination_file = os.path.join(target_folder, filename)
        if not os.path.exists(destination_file):
            missing_files.append(filename)
        all_files.append(os.path.join(path, filename))
    return all_files, missing_files


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


class S3ElsevierSpider(XMLFeedSpider):
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

    allowed_article_types = [
        'research-article',
        'corrected-article',
        'original-article',
        'introduction',
        'letter',
        'correction',
        'addendum',
        'review-article',
        'rapid-communications'
    ]

    ERROR_CODES = range(400, 432)

    def __init__(self, package_path=None, folder=ELSEVIER_SOURCE_DIR, *args, **kwargs):
        """Construct Elsevier spider."""
        super(S3ElsevierSpider, self).__init__(*args, **kwargs)
        self.folder = folder
        self.target_folder = ELSEVIER_DOWNLOAD_DIR,
        self.package_path = package_path
        self.target_folder = self.target_folder[0]

        if not os.path.exists(self.target_folder):
            os.makedirs(self.target_folder)

    def get_authors(self, node):
        """Get the authors."""
        authors = []

        if node.xpath(".//author"):
            for author_group in node.xpath(".//author-group"):
                collaborations = author_group.xpath(
                    ".//collaboration/text/text()").extract()
                for author in author_group.xpath("./author"):
                    surname = author.xpath("./surname/text()")
                    given_names = author.xpath("./given-name/text()")
                    affiliations = self._get_affiliations(author_group, author)
                    orcid = self._get_orcid(author)
                    emails = author.xpath("./e-address/text()")

                    auth_dict = {}
                    if surname:
                        auth_dict['surname'] = surname.extract_first()
                    if given_names:
                        auth_dict['given_names'] = given_names.extract_first()
                    if orcid:
                        auth_dict['orcid'] = orcid
                    if affiliations:
                        auth_dict['affiliations'] = [{"value": aff} for aff in affiliations]
                    if emails:
                        auth_dict['email'] = emails.extract_first()
                    if collaborations:
                        auth_dict['collaborations'] = collaborations
                    authors.append(auth_dict)
        elif node.xpath('.//creator'):
            for author in node.xpath('.//creator/text()'):
                authors.append({'raw_name': author.extract()})

        return authors

    @staticmethod
    def _get_orcid(author):
        """Return an authors ORCID number."""
        orcid_raw = author.xpath("./@orcid").extract_first()
        if orcid_raw:
            return u"ORCID:{0}".format(orcid_raw)

    @staticmethod
    def _find_affiliations_by_id(author_group, ref_ids):
        """Return affiliations with given ids.

        Affiliations should be standardized later.
        """
        affiliations_by_id = []
        for aff_id in ref_ids:
            ce_affiliation = author_group.xpath("//affiliation[@id='" + aff_id + "']")
            if ce_affiliation.xpath(".//affiliation"):
                aff = ce_affiliation.xpath(".//*[self::organization or self::city or self::country]/text()")
                affiliations_by_id.append(", ".join(aff.extract()))
            elif ce_affiliation:
                aff = ce_affiliation.xpath("./textfn/text()").extract_first()
                aff = re.sub(r'^(\d+\ ?)', "", aff)
                affiliations_by_id.append(aff)

        return affiliations_by_id

    def _get_affiliations(self, author_group, author):
        """Return one author's affiliations.

        Will extract authors affiliation ids and call the
        function _find_affiliations_by_id().
        """
        ref_ids = author.xpath(".//@refid").extract()
        group_affs = author_group.xpath(".//affiliation[not(@*)]/textfn/text()")
        all_group_affs = author_group.xpath(".//affiliation/textfn/text()")
        # Don't take correspondence (cor1) or deceased (fn1):
        ref_ids = [refid for refid in ref_ids if "aff" in refid]
        affiliations = []
        if ref_ids:
            affiliations = self._find_affiliations_by_id(author_group, ref_ids)
        if group_affs:
            affiliations += group_affs.extract()

        # if we have no affiliations yet, we got a bad xml, without affiliation cross references.
        # in these cases it seems all group affiliation should be attached to all authors.
        if not affiliations:
            affiliations = all_group_affs.extract()

        return affiliations

    def start_requests(self):
        """List selected folder on locally mounted remote SFTP and yield new tar files."""
        if self.package_path:
            # add local package name without 'file://'
            meta = {'local_filename': self.package_path[7:]}

            yield Request(self.package_path, callback=self.handle_package, meta=meta)
        else:
            params = {}
            new_files, missing_files = list_files(
                self.folder,
                self.target_folder,
            )
            # TODO - add checking if the package was already downloaded
            # Cast to byte-string for scrapy compatibility
            for remote_file in missing_files:
                # TODO download only packages where _ready.xml exists
                if '.tar' in remote_file or '.zip' in remote_file:
                    params["local_filename"] = os.path.join(
                        self.target_folder,
                        remote_file
                    )
                    remote_url = 'file://' + os.path.join('localhost', '/mnt/elsevier-sftp', remote_file)
                    yield Request(
                        str(remote_url),
                        meta=params,
                        callback=self.handle_package)

    def handle_package(self, response):
        """Handle the zip package and yield a request for every XML found."""
        import traceback
        with open(response.meta["local_filename"], 'w') as destination_file:
            destination_file.write(response.body)
        filename = os.path.basename(response.url).rstrip("A.tar").rstrip('.zip')
        # TMP dir to extract zip packages:
        target_folder = mkdtemp(prefix=filename + "_", dir=ELSEVIER_UNPACK_FOLDER)

        zip_filepath = response.meta["local_filename"]
        files = uncompress(zip_filepath, target_folder)

        # The xml files shouldn't be removed after processing; they will
        # be later uploaded to Inspire. So don't remove any tmp files here.
        try:
            for f in files:
                if 'dataset.xml' in f:
                    from scrapy.selector import Selector
                    with open(f, 'r') as dataset_file:
                        dataset = Selector(text=dataset_file.read())
                        data = []
                        for i, issue in enumerate(dataset.xpath('//journal-issue')):
                            tmp = {}
                            tmp['volume'] = "%s %s" % (
                                issue.xpath('//volume-issue-number/vol-first/text()')[0].extract(),
                                issue.xpath('//volume-issue-number/suppl/text()')[0].extract())
                            tmp['issue'] = issue.xpath('//issn/text()')[0].extract()
                            issue_file = os.path.join(target_folder, filename,
                                                      issue.xpath('./files-info/ml/pathname/text()')[0].extract())
                            arts = {}
                            with open(issue_file, 'r') as issue_file:
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
                                    arts[doi] = {'files': {'xml': None, 'pdf': None},
                                                 'first-page': first_page,
                                                 'last-page': last_page}
                            tmp['articles'] = arts
                            data.append(tmp)
                        tmp_empty_data = 0
                        if not data:
                            tmp_empty_data = 1
                            data.append({'volume': None, 'issue': None, 'articles': {}})
                        for article in dataset.xpath('//journal-item'):
                            doi = article.xpath('./journal-item-unique-ids/doi/text()')[0].extract()
                            if article.xpath('./journal-item-properties/online-publication-date/text()'):
                                publication_date = article.xpath(
                                    './journal-item-properties/online-publication-date/text()')[0].extract()[:18]
                            else:
                                publication_date = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
                            journal = article.xpath('./journal-item-unique-ids/jid-aid/jid/text()')[0].extract()
                            if journal == "PLB":
                                journal = "Physics Letters B"
                            if journal == "NUPHB":
                                journal = "Nuclear Physics B"

                            if tmp_empty_data:
                                data[0]['articles'][doi] = {'files': {'xml': None, 'pdf': None}, 'first-page': None,
                                                            'last-page': None, }
                            for i, issue in enumerate(data):
                                if doi in data[i]['articles']:
                                    data[i]['articles'][doi]['journal'] = journal
                                    data[i]['articles'][doi]['publication-date'] = publication_date
                                    xml = os.path.join(target_folder, filename,
                                                       article.xpath('./files-info/ml/pathname/text()')[0].extract())
                                    pdf = os.path.join(target_folder, filename,
                                                       article.xpath('./files-info/web-pdf/pathname/text()')[
                                                           0].extract())
                                    data[i]['articles'][doi]['files']['xml'] = xml
                                    data[i]['articles'][doi]['files']['pdf'] = pdf
                                    if 'vtex' in zip_filepath:
                                        pdfa = os.path.join(os.path.split(pdf)[0], 'main_a-2b.pdf')
                                        pdfa = os.path.join(target_folder, pdfa)
                                        data[i]['articles'][doi]['files']['pdfa'] = pdfa
                        for i, issue in enumerate(data):
                            print('a')
                            for doi in data[i]['articles']:
                                print('b')
                                try:
                                    print('try')
                                    xml_file = open(data[i]['articles'][doi]['files']['xml'], 'r')
                                    print(xml_file)
                                    xml_file_content = xml_file.read()
                                    for nodename in self.itertag:
                                        print(nodename)
                                        for selector in xmliter(xml_file_content, nodename):
                                            print(selector)
                                            yield self.parse_node(data[i], doi, zip_filepath, selector)
                                except:
                                    print(traceback.print_exc())
        except:
            import traceback
            traceback.print_exc()

    def parse_node(self, meta, doi, package_path, node):
        """Parse a OUP XML file into a HEP record."""
        print("Parsing node")
        print(meta)
        node.remove_namespaces()
        article_type = node.xpath('@article-type').extract()
        self.log("Got article_type {0}".format(article_type))

        record = HEPLoader(item=HEPRecord(), selector=node)
        if article_type in ['correction', 'addendum']:
            record.add_xpath('related_article_doi', "//related-article[@ext-link-type='doi']/@href")
            record.add_value('journal_doctype', article_type)

        record.add_value('dois', [doi])
        record.add_xpath('page_nr', "//counts/page-count/@count")

        record.add_xpath('abstract', '//abstract[1]/abstract-sec')
        record.add_xpath('title', '//title/text()')
        record.add_xpath('subtitle', '//subtitle/text()')

        record.add_value('authors', self.get_authors(node))
        record.add_xpath('collaborations', "//contrib/collab/text()")

        # TODO: Special journal title handling
        record.add_value('journal_title', meta['articles'][doi]['journal'])
        record.add_value('journal_issue', meta['issue'])
        record.add_value('journal_volume', meta['volume'])
        record.add_xpath('journal_artid', '//item-info/aid/text()')

        record.add_value('journal_fpage', meta['articles'][doi]['first-page'])
        record.add_value('journal_lpage', meta['articles'][doi]['last-page'])

        published_date = datetime.datetime.strptime(meta['articles'][doi]['publication-date'], "%Y-%m-%dT%H:%M:%S")
        record.add_value('journal_year', published_date.year)
        record.add_value('date_published', published_date.strftime("%Y-%m-%d"))

        record.add_xpath('copyright_holder', '//copyright/text()')
        record.add_xpath('copyright_year', '//copyright/@year')
        record.add_xpath('copyright_statement', '//copyright/text()')
        record.add_value('copyright_material', 'Article')

        license = get_license(
            license_url='http://creativecommons.org/licenses/by/3.0/'
        )
        record.add_value('license', license)

        record.add_value('collections', [meta['articles'][doi]['journal']])

        # local fiels paths
        local_files = []
        for filetype in meta['articles'][doi]['files']:
            local_files.append({'filetype': filetype, 'path': meta['articles'][doi]['files'][filetype]})
        record.add_value('local_files', local_files)

        parsed_record = dict(record.load_item())

        print(parsed_record)
        return parsed_record
