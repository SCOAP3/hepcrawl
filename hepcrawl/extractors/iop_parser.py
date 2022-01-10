import logging

from hepcrawl.extractors.jats import Jats
from hepcrawl.items import HEPRecord
from hepcrawl.loaders import HEPLoader
from hepcrawl.utils import get_license

logger = logging.getLogger(__name__)


class IOPParser(Jats):
    article_type_mapping = {
        'research-article': 'article',
        'corrected-article': 'article',
        'original-article': 'article',
        'correction': 'corrigendum',
        'addendum': 'addendum',
        'editorial': 'editorial'
    }

    def parse_node(self, response, node):
        """Parse a IOP XML file into a HEP record."""
        node.remove_namespaces()
        record = HEPLoader(item=HEPRecord(), selector=node, response=response)

        dois = node.xpath("//article-id[@pub-id-type='doi']/text()").extract()
        record.add_value('dois', dois)

        raw_article_type = node.xpath('//@article-type').extract()
        article_type = map(lambda x: self.article_type_mapping.get(x, 'other'), raw_article_type)
        record.add_value('journal_doctype', article_type)

        if 'other' in article_type:
            logger.warning('There are unmapped article types for article %s with types %s.' % (
                dois, raw_article_type))

        if article_type in ['correction', 'addendum']:
            logger.info('Adding related_article_doi.')
            record.add_xpath('related_article_doi', "//related-article[@ext-link-type='doi']/@href")

        arxiv_eprints = self.get_arxiv_eprints(node)
        if not arxiv_eprints:
            logger.warning('No arxiv eprints found for article %s.' % dois)
        else:
            record.add_value('arxiv_eprints', arxiv_eprints)

        page_nr = node.xpath("//counts/page-count/@count")
        if page_nr:
            try:
                page_nr = map(int, page_nr.extract())
                record.add_value('page_nr', page_nr)
            except ValueError as e:
                logger.error('Failed to parse last_page or first_page for article %s: %s' % (dois, e))

        record.add_xpath('abstract', '(//abstract[1]//text())[2]')
        record.add_xpath('title', '//article-title/text()')
        record.add_xpath('subtitle', '//subtitle/text()')

        authors = self._get_authors(node)
        if not authors:
            logger.error('No authors found for article %s.' % dois)
        record.add_value('authors', authors)
        record.add_xpath('collaborations', "//contrib/collab/text()")

        record.add_value('date_published', self._get_published_date(node))

        record.add_xpath('journal_title', '//abbrev-journal-title/text()|//journal-title/text()')
        record.add_xpath('journal_issue', '//issue/text()')
        record.add_xpath('journal_volume', '//volume/text()')
        record.add_xpath('journal_artid', '//elocation-id/text()')

        published_date = self._get_published_date(node)
        record.add_value('journal_year', int(published_date[:4]))
        record.add_value('date_published', published_date)

        record.add_xpath('copyright_holder', '//copyright-holder/text()')
        record.add_xpath('copyright_year', '//copyright-year/text()')
        record.add_xpath('copyright_statement', '//copyright-statement/text()')

        license = get_license(
            license_url=node.xpath('//license/license-p/ext-link/text()').extract_first()
        )
        record.add_value('license', license)

        record.add_value('collections', ['Chinese Physics C'])

        # local file paths
        local_files = []
        if 'xml_url' in response.meta:
            local_files.append({'filetype': 'xml', 'path': response.meta['xml_url']})
        if 'pdf_url' in response.meta:
            local_files.append({'filetype': 'pdf', 'path': response.meta['pdf_url']})
        if 'pdfa_url' in response.meta:
            local_files.append({'filetype': 'pdf/a', 'path': response.meta['pdfa_url']})
        record.add_value('local_files', local_files)

        return dict(record.load_item())

    def get_arxiv_eprints(self, node):
        arxiv_eprints = []

        arxivs_raw = node.xpath("//article-id[@pub-id-type='arxiv']/text()")
        for arxiv in arxivs_raw:
            ar = arxiv.extract().replace('arXiv:', '')
            if ar:
                arxiv_eprints.append({'value': ar})

        return arxiv_eprints
