from ast import parse
import pytest

from hepcrawl.extractors import hindawi_parser
import os

from scrapy.selector import Selector

file_for_testing = '2022_hindawi.xml'
correct_affiliations = u'2109.02769'


@pytest.fixture
def arxiv_from_records(shared_datadir):
    parser = hindawi_parser.HindawiParser()
    content = (shared_datadir / file_for_testing).read_text()
    selector = Selector(text=content, type='xml')
    arxiv = parser.get_arxivs(selector, '0000')
    assert arxiv
    return arxiv


def test_arxiv_in_Hindawi(arxiv_from_records):
    assert correct_affiliations == arxiv_from_records[0]['value']
