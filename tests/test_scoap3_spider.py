import pytest

from hepcrawl.spiders import scoap3_spider
from tests.responses import fake_response_from_file, get_node


@pytest.fixture
def cpc_record():
    """Return the results from the Hindawi spider."""

    file = 'scoap3/cpc.xml'
    spider = scoap3_spider.Scoap3Spider()
    response = fake_response_from_file(file)
    nodes = get_node(spider, "//marc:record", response)

    record = spider.parse_node(response, nodes[0])

    assert record
    return record


def test_cpc_title(cpc_record):
    assert cpc_record['title'] == 'Chiral phase transition from the Dyson-Schwinger equations in a finite spherical ' \
                                  'volume Supported by the National Natural Science Foundation of China (11475085, 11' \
                                  '535005, 11690030, 11574145)'


def test_cpc_date_published(cpc_record):
    assert cpc_record['date_published'] == '2019-06-01'


def test_cpc_authors(cpc_record):
    assert cpc_record['authors'] == [
        {'affiliations': [{'value': 'School of Physics, Nanjing University, Nanjing 210093, China'}],
         'full_name': 'Zhao, Ya-Peng',
         'given_names': 'Ya-Peng',
         'raw_name': 'Zhao, Ya-Peng',
         'surname': 'Zhao'},
        {'affiliations': [{'value': 'School of Physics, Nanjing University, Nanjing 210093, China'}],
         'full_name': 'Zhang, Rui-Rui',
         'given_names': 'Rui-Rui',
         'raw_name': 'Zhang, Rui-Rui',
         'surname': 'Zhang'},
        {'affiliations': [{'value': 'School of Physics, Nanjing University, Nanjing 210093, China'},
                          {
                              'value': 'Collaborative Innovation Center of Advanced Microstructures, Nanjing Universit'
                                       'y, Nanjing 210093, China'}],
         'full_name': 'Zhang, Han',
         'given_names': 'Han',
         'raw_name': 'Zhang, Han',
         'surname': 'Zhang'},
        {'affiliations': [{'value': 'Joint Center for Particle, Nuclear Physics and Cosmology, Nanjing 210093, China'},
                          {'value': 'School of Physics, Nanjing University, Nanjing 210093, China'},
                          {
                              'value': 'State Key Laboratory of Theoretical Physics, Institute of Theoretical Physics,'
                                       ' CAS, Beijing 100190, China'}],
         'full_name': 'Zong, Hong-Shi',
         'given_names': 'Hong-Shi',
         'raw_name': 'Zong, Hong-Shi',
         'surname': 'Zong'}]


def test_cpc_dois(cpc_record):
    assert cpc_record['dois'] == [{'value': '10.1088/1674-1137/43/6/063101'}]


def test_cpc_journal_title(cpc_record):
    assert cpc_record['journal_title'] == 'Chinese Physics C'


def test_cpc_year(cpc_record):
    assert cpc_record['journal_year'] == 2019


def test_cpc_page_nr(cpc_record):
    assert cpc_record['page_nr'] == [5]
