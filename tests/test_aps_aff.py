from __future__ import absolute_import, print_function, unicode_literals

from scrapy.http import TextResponse
from hepcrawl.spiders import aps_spider
from .responses import fake_response_from_file


def test_aps_aff_note():
    test_file = 'aps/aps_note_affiliation.json'
    fake_response = fake_response_from_file(
        test_file,
        response_type=TextResponse,
    )
    spider = aps_spider.APSSpider()
    records = list(spider.parse(fake_response))

    assert records
    assert len(records) == 1

    expected_authors = [
            {'affiliations': [{'value': u'Department of Physics, University of Turin and INFN, Turin, Via '
                                        u'Pietro Giuria 1, I-10125 Turin, Italy'}],
             'full_name': u'Caselle, Michele',
             'given_names': u'Michele',
             'raw_name': u'Michele Caselle',
             'surname': u'Caselle'},
            {'affiliations': [
                {'value': u'Department of Physics, University of Turin and INFN, Turin, '
                         u'Via Pietro Giuria 1, I-10125 Turin, Italy'},
                {'value': u'SISSA and INFN, Sezione di Trieste, Via Bonomea 265, 34136 '
                             u'Trieste, Italy'}],
                'full_name': u'Sorba, Marianna',
                'given_names': u'Marianna',
                'raw_name': u'Marianna Sorba',
                'surname': u'Sorba'},
    ]

    assert records[0]['authors'] == expected_authors
