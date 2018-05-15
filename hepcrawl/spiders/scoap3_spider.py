# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2016 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Spider for Hindawi."""

from __future__ import absolute_import, print_function

import os

from scrapy import Request
from scrapy.spiders import XMLFeedSpider

from ..items import HEPRecord
from ..loaders import HEPLoader
from ..utils import get_license, get_first


class Scoap3Spider(XMLFeedSpider):

    """SCOAP3 crawler

    OAI interface: http://www.hindawi.com/oai-pmh/
    Example:
    http://www.hindawi.com/oai-pmh/oai.aspx?verb=listrecords&set=HINDAWI.AA&metadataprefix=marc21&from=2015-01-01

    Sets to use:
    HINDAWI.AA (Advances in Astronomy)
    HINDAWI.AHEP (Advances in High Energy Physics)
    HINDAWI.AMP (Advances in Mathematical Physics)
    HINDAWI.JAS (Journal of Astrophysics)
    HINDAWI.JCMP (Journal of Computational Methods in Physics)
    HINDAWI.JGRAV (Journal of Gravity)

    Scrapes Hindawi metadata XML files one at a time.
    The actual files should be retrieved from Hindawi via its OAI interface.
    The file can contain multiple records.

    1. The spider will parse the local MARC21XML format file for record data

    2. Finally a HEPRecord will be created.


    Example usage:
    .. code-block:: console

        scrapy crawl hindawi -a source_file=file://`pwd`/tests/responses/hindawi/test_1.xml

    Happy crawling!
    """

    name = 'scoap3'
    start_urls = []
    iterator = 'xml'
    itertag = 'marc:record'

    namespaces = [
        ("OAI-PMH", "http://www.openarchives.org/OAI/2.0/"),
        ("marc", "http://www.loc.gov/MARC21/slim"),
        ("mml", "http://www.w3.org/1998/Math/MathML"),
    ]

    def __init__(self, source_file=None, *args, **kwargs):
        """Construct Hindawi spider."""
        super(Scoap3Spider, self).__init__(*args, **kwargs)
        self.source_file = source_file

    def start_requests(self):
        """Default starting point for scraping shall be the local XML file."""
        yield Request(self.source_file)

    @staticmethod
    def get_affiliations(author):
        """Get the affiliations of an author."""
        affiliations_raw = author.xpath(
            "./subfield[@code='v' or @code='u']/text()").extract()
        affiliations_raw = set(affiliations_raw)
        affiliations = []
        for aff in affiliations_raw:
            affiliations.append(
                {"value": aff}
            )

        return affiliations

    def get_authors(self, node):
        """Gets the authors."""
        authors_first = node.xpath("./datafield[@tag='100']")
        authors_others = node.xpath("./datafield[@tag='700']")
        authors_raw = authors_first + authors_others
        authors = []
        for author in authors_raw:
            orcid = author.xpath("./subfield[@code='j']/text()").extract_first()
            if orcid:
                if orcid.startswith("ORCID"):
                    orcid = orcid[6:]
                authors.append({
                    'raw_name': author.xpath("./subfield[@code='a']/text()").extract_first(),
                    'affiliations': self.get_affiliations(author),
                    'orcid': orcid,
                })
            else:
                authors.append({
                    'raw_name': author.xpath("./subfield[@code='a']/text()").extract_first(),
                    'affiliations': self.get_affiliations(author),
                })

        return authors

    def get_arxivs(self, node):
        """Gets the authors."""
        arxivs_raw = node.xpath("./datafield[@tag='037'][subfield[@code='9'][contains(text(), 'arXiv')]]")
        arxivs = []
        for arxiv in arxivs_raw:
            ar = arxiv.xpath("./subfield[@code='a']/text()").extract_first()
            if ar:
                arxivs.append({
                    'source': 'arXiv',
                    'value': ar
                })
        return arxivs

    # # TODO: change this
    # def get_urls_in_record(self, node):
    #     """Return all the different urls in the xml."""
    #     marc_856 = node.xpath(
    #         "./datafield[@tag='856']/subfield[@code='u']/text()").extract()
    #     marc_FFT = node.xpath(
    #         "./datafield[@tag='FFT']/subfield[@code='a']/text()").extract()
    #     all_links = list(set(marc_856 + marc_FFT))

    #     return self.differentiate_urls(all_links)

    # @staticmethod
    # def differentiate_urls(urls_in_record):
    #     """Determine what kind of urls the record has."""
    #     pdf_links = []
    #     xml_links = []
    #     splash_links = []
    #     for link in urls_in_record:
    #         if "pdf" in link.lower():
    #             pdf_links.append(link)
    #         elif "xml" in link.lower():
    #             xml_links.append(link)
    #         elif "dx.doi.org" in link.lower():
    #             splash_links.append(link)

    #     return (
    #         pdf_links,
    #         xml_links,
    #         splash_links,
    #     )

    @staticmethod
    def get_copyright(node):
        """Get copyright year and statement."""
        copyright_raw = node.xpath(
            "./datafield[@tag='542']/subfield[@code='f']/text()").extract_first()
        cr_year = ""
        if copyright_raw:
            cr_year = "".join(i for i in copyright_raw if i.isdigit())

        return copyright_raw, cr_year

    @staticmethod
    def get_journal_pages(node):
        """Get copyright fpage and lpage."""
        journal_pages = node.xpath(
            "./datafield[@tag='773']/subfield[@code='c']/text()").extract_first()
        if journal_pages and '-' in journal_pages:
            return journal_pages.split('-', 1)
        else:
            return journal_pages, ''

    @staticmethod
    def get_journal_title(node):
        JOURNAL_FULL_NAMES = {
            "PTEP": "Progress of Theoretical and Experimental Physics",
            "New J. Phys.": "New Journal of Physics",
            "JCAP": "Journal of Cosmology and Astroparticle Physics",
            "EPJC": "European Physical Journal C",
            "Chinese Phys. C": "Chinese Physics C",
            "JHEP": "Journal of High Energy Physics",
            "Physics letters B": "Physics Letters B",
            "Phys. Rev. C": "Physical Review C",
            "Phys. Rev. D": "Physical Review D",
            "Phys. Rev. Lett.": "Physical Review Letters"
        }
        title = node.xpath("./datafield[@tag='773']/subfield[@code='p']/text()").extract_first()
        for abreviation, full_name in JOURNAL_FULL_NAMES.items():
            if title == abreviation:
                title = full_name
                break
        return title

    # def create_fft_file(self, file_path, file_access, file_type):
    #     """Create a structured dictionary to add to 'files' item."""
    #     file_dict = {
    #         "access": file_access,
    #         "description": self.name.upper(),
    #         "url": file_path,
    #         "type": file_type,
    #     }
    #     return file_dict

    def parse_node(self, response, node):
        """Iterate all the record nodes in the XML and build the HEPRecord."""

        node.remove_namespaces()
        record = HEPLoader(item=HEPRecord(), selector=node, response=response)

        record.add_value('authors', self.get_authors(node))
        record.add_xpath('abstract', "./datafield[@tag='520']/subfield[@code='a']")
        record.add_xpath('title',
                         "./datafield[@tag='245']/subfield[@code='a']/text()")
        record.add_xpath('date_published',
                         "./datafield[@tag='260']/subfield[@code='c']/text()")
        record.add_xpath('page_nr',
                         "./datafield[@tag='300']/subfield[@code='a']/text()")
        record.add_xpath('dois',
                         "./datafield[@tag='024' and @ind1='7'][subfield[@code='2'][contains(text(), 'DOI')]]/subfield[@code='a']/text()")
        record.add_value('journal_title', self.get_journal_title(node))
        record.add_xpath('journal_volume',
                         "./datafield[@tag='773']/subfield[@code='a']/text()")

        # record.add_xpath('arxiv_eprints',
        #                  "./datafield[@tag='037'][subfield[@code='9'][contains(text(), 'arXiv')]]/subfield[@code='a']/text()")
        record.add_value('report_numbers', self.get_arxivs(node))
        journal_year = node.xpath(
            "./datafield[@tag='773']/subfield[@code='y']/text()"
        ).extract()
        if journal_year:
            record.add_value('journal_year', int(journal_year[0]))

        record.add_xpath('journal_issue',
                         "./datafield[@tag='773']/subfield[@code='n']/text()")

        fpage, lpage = self.get_journal_pages(node)
        record.add_value('journal_fpage', fpage)
        record.add_value('journal_lpage', lpage)

        cr_statement, cr_year = self.get_copyright(node)
        record.add_value('copyright_statement', cr_statement)
        record.add_value('copyright_year', cr_year)

        license = get_license(
            license_url=node.xpath(
                "./datafield[@tag='540']/subfield[@code='u']/text()"
            ).extract_first(),
            license_text=node.xpath(
                "./datafield[@tag='540']/subfield[@code='a']/text()"
            ).extract_first(),
        )
        record.add_value('license', license)

        # pdf_links, xml_links, splash_links = self.get_urls_in_record(node)
        # record.add_value('urls', splash_links)
        # record.add_value('file_urls', pdf_links)
        # if xml_links:
        #     record.add_value('additional_files',
        #                      [self.create_fft_file(xml,
        #                                            "INSPIRE-HIDDEN",
        #                                            "Fulltext") for xml in xml_links])
        local_files = []

        for file_node in node.xpath("./datafield[@tag='856']"):
            file_extension = file_node.xpath("./subfield[@code='x']/text()").extract_first()
            file_url = file_node.xpath("./subfield[@code='u']/text()").extract_first()
            if "repo.scoap3" not in file_url:
                continue
            if not file_extension:
                tmp, file_extension = os.path.splitext(file_url)
                file_extension = file_extension.lower().strip('.')
            local_files.append({'filetype':file_extension, 'path':file_url})

        record.add_value('local_files', local_files)
        record.add_xpath('source',
                         "./datafield[@tag='260']/subfield[@code='b']/text()")

        #record.add_xpath('record_creation_date', "./datafield[@tag='592']/subfield[@code='a']/text()")
        control_number = node.xpath("./controlfield[@tag='001']/text()").extract_first()
        record.add_value('control_number', control_number)

        return record.load_item()
