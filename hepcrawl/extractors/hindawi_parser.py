import logging

from ..items import HEPRecord
from ..loaders import HEPLoader
from ..utils import get_license

logger = logging.getLogger(__name__)


class HindawiParser(object):

    def parse_node(self, response, node):
        """Iterate all the record nodes in the XML and build the HEPRecord."""

        node.remove_namespaces()
        record = HEPLoader(item=HEPRecord(), selector=node, response=response)

        record.add_value('authors', self.get_authors(node))
        record.add_xpath('abstract', "./datafield[@tag='520']/subfield[@code='a']")
        record.add_xpath('title', "./datafield[@tag='245']/subfield[@code='a']/text()")
        record.add_xpath('date_published', "./datafield[@tag='260']/subfield[@code='c']/text()")
        page_nr = node.xpath("./datafield[@tag='300']/subfield[@code='a']/text()")
        if page_nr:
            page_nr = map(int, page_nr.extract())
            record.add_value('page_nr', page_nr)
        record.add_xpath('dois',
                         "./datafield[@tag='024'][subfield[@code='2'][contains(text(), 'DOI')]]/subfield[@code='a']/text()")
        record.add_xpath('journal_title', "./datafield[@tag='773']/subfield[@code='p']/text()")
        record.add_xpath('journal_volume', "./datafield[@tag='773']/subfield[@code='a']/text()")
        record.add_value('arxiv_eprints', self.get_arxivs(node))

        journal_year = node.xpath("./datafield[@tag='773']/subfield[@code='y']/text()").extract()
        if journal_year:
            record.add_value('journal_year', int(journal_year[0]))

        record.add_xpath('journal_issue', "./datafield[@tag='773']/subfield[@code='n']/text()")

        fpage, lpage = self.get_journal_pages(node)
        record.add_value('journal_fpage', fpage)
        record.add_value('journal_lpage', lpage)

        cr_statement, cr_year = self.get_copyright(node)
        record.add_value('copyright_statement', cr_statement)
        record.add_value('copyright_year', cr_year)

        license = get_license(
            license_url=node.xpath("./datafield[@tag='540']/subfield[@code='u']/text()").extract_first(),
            license_text=node.xpath("./datafield[@tag='540']/subfield[@code='a']/text()").extract_first(),
        )
        record.add_value('license', license)

        record.add_value('collections', ['Advances in High Energy Physics'])
        record.add_xpath('source', "./datafield[@tag='260']/subfield[@code='b']/text()")

        return record.load_item()

    @staticmethod
    def get_affiliations(author):
        """Get the affiliations of an author."""
        affiliations_raw = author.xpath("./subfield[@code='u']/text()").extract()

        return [{"value": aff} for aff in affiliations_raw]

    def get_authors(self, node):
        """Gets the authors."""
        authors_first = node.xpath("./datafield[@tag='100']")
        authors_others = node.xpath("./datafield[@tag='700']")
        authors_raw = authors_first + authors_others
        authors = []
        for author in authors_raw:
            orcid = author.xpath("./subfield[@code='j']/text()").extract_first()
            if orcid:
                if orcid.startswith("ORCID-"):
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

        if not authors:
            logger.error('No authors found.')

        return authors

    def get_arxivs(self, node):
        """Gets the authors."""
        arxivs_raw = node.xpath("./datafield[@tag='037'][subfield[@code='9'][contains(text(), 'arXiv')]]")
        arxivs = []

        for arxiv in arxivs_raw:
            ar = arxiv.xpath("./subfield[@code='a']/text()").extract_first().replace('arXiv:', '')
            if ar:
                arxivs.append({'value': ar})

        if not arxivs:
            logger.error('No arxiv found.')

        return arxivs

    @staticmethod
    def get_copyright(node):
        """Get copyright year and statement."""
        copyright_raw = node.xpath("./datafield[@tag='542']/subfield[@code='f']/text()").extract_first()
        cr_year = "".join(i for i in copyright_raw if i.isdigit())

        return copyright_raw, cr_year

    @staticmethod
    def get_journal_pages(node):
        """Get copyright fpage and lpage."""
        journal_pages = node.xpath("./datafield[@tag='773']/subfield[@code='c']/text()").extract_first()
        if '-' in journal_pages:
            return journal_pages.split('-', 1)
        else:
            return journal_pages, ''
