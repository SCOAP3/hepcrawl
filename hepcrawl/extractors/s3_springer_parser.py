import datetime
import logging
import re

from ..items import HEPRecord
from ..loaders import HEPLoader
from ..utils import get_first

logger = logging.getLogger(__name__)


class S3SpringerParser(object):
    article_type_mapping = {
        "OriginalPaper": "article",
        "ReviewPaper": "review",
        "BriefCommunication": "article",
        "EditorialNotes": "editorial",
        "BookReview": "review",
        "ContinuingEducation": "other",
        "Interview": "other",
        "Letter": "other",
        "Erratum": "erratum",
        "Legacy": "other",
        "Abstract": "other",
        "Report": "other",
        "Announcement": "other",
        "News": "other",
        "Events": "other",
        "Acknowledgments": "other",
        "MediaReport": "other",
        "BibliographicalNote": "other",
        "ProductNotes": "other",
        "Unknown": "other"
    }

    def parse_node(self, response, node):
        """Parse a Springer XML file into a HEP record."""
        node.remove_namespaces()
        record = HEPLoader(item=HEPRecord(), selector=node, response=response)

        article_type = node.xpath('//Article/ArticleInfo/@ArticleType').extract()
        article_type = map(lambda x: self.article_type_mapping.get(x, 'other'), article_type)
        record.add_value('journal_doctype', article_type)

        dois = node.xpath("//ArticleDOI/text()").extract()
        record.add_value('dois', dois)

        arxiv_eprints = self._get_arxiv_eprints(node)
        if not arxiv_eprints:
            logger.warning('No arxiv eprints found for article %s.' % dois)
        else:
            record.add_value('arxiv_eprints', arxiv_eprints)

        # extract first and last page, then calculate the number of pages
        first_pages = node.xpath('//ArticleFirstPage/text()').extract()
        last_pages = node.xpath('//ArticleLastPage/text()').extract()
        if first_pages and last_pages:
            try:
                page_nrs = map(lambda (first, last): int(last) - int(first) + 1, zip(first_pages, last_pages))
                record.add_value('page_nr', page_nrs)
            except ValueError as e:
                logger.error('Failed to parse last_page or first_page for article %s: %s' % (dois, e))

        record.add_xpath('abstract', '//Article/ArticleHeader/Abstract/Para')

        title = node.xpath('//ArticleTitle')
        title = re.sub('<math>.*?</math>', '', title.extract()[0])
        record.add_value('title', title)

        record.add_value('authors', self._get_authors(node, dois))
        record.add_xpath('collaborations', '//InstitutionalAuthor/InstitutionalAuthorName/text()')

        journal = node.xpath('//JournalTitle/text()').extract()[0].lstrip('The ')
        record.add_value('journal_title', journal)
        record.add_xpath('journal_issue', '//IssueIDStart/text()')
        record.add_xpath('journal_volume', '//VolumeIDStart/text()')
        record.add_xpath('journal_artid', '//Article/@ID')

        record.add_xpath('journal_fpage', '//ArticleFirstPage/text()')
        record.add_xpath('journal_lpage', '//ArticleLastPage/text()')

        published_date = self._get_published_date(node)
        record.add_value('journal_year', published_date.year)
        record.add_value('date_published', published_date.isoformat())

        record.add_xpath('copyright_holder', '//ArticleCopyright/CopyrightHolderName/text()')
        record.add_xpath('copyright_year', '//ArticleCopyright/CopyrightYear/text()')
        record.add_xpath('copyright_statement', '//ArticleCopyright/copyright-statement/text()')

        record.add_value('license', self._get_license(node, dois))

        record.add_value('collections', [journal])

        # local file paths
        local_files = []
        if 'xml_url' in response.meta:
            local_files.append({'filetype': 'xml', 'path': response.meta['xml_url'].replace('file://', '')})
        if 'pdfa_url' in response.meta:
            local_files.append({'filetype': 'pdf/a', 'path': response.meta['pdfa_url'].replace('file://', '')})

        record.add_value('local_files', local_files)

        return dict(record.load_item())

    def _get_published_date(self, node):
        year = node.xpath('//OnlineDate/Year/text()').extract()[0]
        month = node.xpath('//OnlineDate/Month/text()').extract()[0]
        day = node.xpath('//OnlineDate/Day/text()').extract()[0]
        return datetime.date(day=int(day), month=int(month), year=int(year))

    def _get_license(self, node, dois):
        license_type = node.xpath('//License/@SubType').extract()
        version = node.xpath('//License/@Version').extract()
        text = "https://creativecommons.org/licenses/"

        if license_type:
            license_type = license_type[0].lower().lstrip('cc ').replace(' ', '-')
            return {
                "license": "CC-" + license_type.upper() + "-" + version[0],
                "url": "%s/%s/%s" % (text, license_type, version[0])
            }

        # return default licence if not found
        logger.warning('Licence not found, returning default licence for article %s.' % dois)
        return {"license": "CC-BY-3.0", "url": "https://creativecommons.org/licenses/by/3.0"}

    def _clean_aff(self, node):
        org_div = node.xpath('./OrgDivision/text()').extract_first()
        org_name = node.xpath('./OrgName/text()').extract_first()
        street = node.xpath('./OrgAddress/Street/text()').extract_first()
        city = node.xpath('./OrgAddress/City/text()').extract_first()
        state = node.xpath('./OrgAddress/State/text()').extract_first()
        postcode = node.xpath('./OrgAddress/Postcode/text()').extract_first()
        country = node.xpath('./OrgAddress/Country/text()').extract_first()

        result = []
        if org_div:
            result.append(org_div)
        if org_name:
            result.append(org_name)
        if street:
            result.append(street)
        if city:
            result.append(city)
        if state:
            result.append(state)
        if postcode:
            result.append(postcode)
        if country:
            result.append(country)

        return ', '.join(result), org_name, country

    def _get_affiliations(self, node, contrib):
        affiliations = []
        referred_id = contrib.xpath("@AffiliationIDS").extract()

        if not referred_id:
            return affiliations

        for ref in referred_id[0].split():
            cleaned_aff = self._clean_aff(node.xpath("//Affiliation[@ID='{0}']".format(ref)))
            if cleaned_aff not in affiliations:
                affiliations.append(cleaned_aff)

        mapped_affiliations = list(
            map(lambda (aff, org, country): {'value': aff, 'organization': org, 'country': country},
                affiliations))

        return mapped_affiliations

    def _get_authors(self, node, dois):
        authors = []
        for contrib in node.xpath("//Author"):
            surname = contrib.xpath("./AuthorName/FamilyName/text()").extract()
            given_names = contrib.xpath("./AuthorName/GivenName/text()").extract()
            email = contrib.xpath("./Contact/Email/text()").extract()

            affiliations = self._get_affiliations(node, contrib)

            authors.append({
                'surname': get_first(surname, ""),
                'given_names': get_first(given_names, ""),
                'affiliations': affiliations,
                'email': get_first(email, ""),
            })

        if not authors:
            logger.error('No authors found for article %s.' % dois)

        return authors

    def _get_arxiv_eprints(self, node):
        arxiv_eprints = []

        for arxiv in node.xpath("//ArticleExternalID[@Type='arXiv']/text()"):
            arxiv_eprints.append({'value': arxiv.extract()})

        return arxiv_eprints
