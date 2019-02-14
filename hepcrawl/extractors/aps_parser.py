import json

import link_header

from hepcrawl.items import HEPRecord
from hepcrawl.loaders import HEPLoader
from hepcrawl.utils import get_nested, get_license, build_dict
from scrapy import Request


class APSParser(object):
    def parse(self, response):
        """Parse a APS JSON file into a HEP record."""
        aps_response = json.loads(response.body_as_unicode())

        for article in aps_response['data']:
            record = HEPLoader(item=HEPRecord(), response=response)

            record.add_value('journal_doctype', article.get('articleType'))
            record.add_value('dois', get_nested(article, 'identifiers', 'doi'))
            record.add_value('page_nr', str(article.get('numPages', '')))

            arxiv = get_nested(article, 'identifiers', 'arxiv').replace('arXiv:', '')
            record.add_value('arxiv_eprints', {'value': arxiv})

            record.add_value('abstract', get_nested(article, 'abstract', 'value'))
            record.add_value('title', get_nested(article, 'title', 'value'))

            authors, collaborations = self._get_authors_and_collab(article)
            record.add_value('authors', authors)
            record.add_value('collaborations', collaborations)

            record.add_value('journal_title', get_nested(article, 'journal', 'name'))
            record.add_value('journal_issue', get_nested(article, 'issue', 'number'))
            record.add_value('journal_volume', get_nested(article, 'volume', 'number'))

            published_date = article['date']
            record.add_value('journal_year', int(published_date[:4]))
            record.add_value('date_published', published_date)
            record.add_value('field_categories', [
                {
                    'term': term.get('label'),
                    'scheme': 'APS',
                    'source': '',
                } for term in get_nested(
                    article,
                    'classificationSchemes',
                    'subjectAreas'
                )
            ])
            copyright_holders = get_nested(article, 'rights', 'copyrightHolders')
            if copyright_holders:
                record.add_value('copyright_holder', copyright_holders[0]['name'])

            record.add_value('copyright_year', str(get_nested(article, 'rights', 'copyrightYear')))
            record.add_value('copyright_statement', get_nested(article, 'rights', 'rightsStatement'))

            license = get_license(
                license_url=get_nested(article, 'rights', 'licenses')[0]['url']
            )
            record.add_value('license', license)

            record.add_value('collections', ['HEP', 'Citeable', 'Published'])
            yield record.load_item()

        # Pagination support. Will yield until no more "next" pages are found
        if 'Link' in response.headers:
            links = link_header.parse(response.headers['Link'])
            next = links.links_by_attr_pairs([('rel', 'next')])
            if next:
                next_url = next[0].href
                yield Request(next_url)

    def _get_authors_and_collab(self, article):
        authors = []
        collaboration = []

        for author in article['authors']:
            if author['type'] == 'Person':
                author_affiliations = []
                if 'affiliations' in article and 'affiliationIds' in author:
                    affiliations = build_dict(article['affiliations'], 'id')
                    for aff_id in author['affiliationIds']:
                        author_affiliations.append({'value': affiliations[aff_id]['name']})

                surname = ''
                given_name = ''
                raw_name = ''
                if author.get('surname'):
                    surname = author.get('surname').replace('\u2009', ' ')
                if author.get('firstname'):
                    given_name = author.get('firstname').replace('\u2009', ' ')
                if author.get('name'):
                    raw_name = author.get('name').replace('\u2009', ' ')

                authors.append({
                    'surname': surname,
                    'given_names': given_name,
                    "raw_name": raw_name,
                    'affiliations': author_affiliations
                })

            elif author['type'] == 'Collaboration':
                collaboration.append(author['name'])

        return authors, collaboration
