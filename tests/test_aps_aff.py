

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
            {'affiliations': [{'value': 'Department of Physics, University of Turin and INFN, Turin, Via '
                                        'Pietro Giuria 1, I-10125 Turin, Italy'}],
             'full_name': 'Caselle, Michele',
             'given_names': 'Michele',
             'raw_name': 'Michele Caselle',
             'surname': 'Caselle'},
            {'affiliations': [
                {'value': 'Department of Physics, University of Turin and INFN, Turin, '
                         'Via Pietro Giuria 1, I-10125 Turin, Italy'},
                {'value': 'SISSA and INFN, Sezione di Trieste, Via Bonomea 265, 34136 '
                             'Trieste, Italy'}],
                'full_name': 'Sorba, Marianna',
                'given_names': 'Marianna',
                'raw_name': 'Marianna Sorba',
                'surname': 'Sorba'},
    ]

    assert records[0]['authors'] == expected_authors
