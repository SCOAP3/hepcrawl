import pytest

from hepcrawl.extractors import iop_parser
import os

from scrapy.selector import Selector

correct_licenses = {
    "abf13a.xml": [
        {"url": "http://creativecommons.org/licenses/by/3.0/", "license": "CC-BY-3.0"}
    ],
    "ac3fab.xml": [
        {"url": "http://creativecommons.org/licenses/by/3.0/", "license": "CC-BY-3.0"}
    ],
    "abb4d6.xml": [
        {"url": "http://creativecommons.org/licenses/by/3.0/", "license": "CC-BY-3.0"}
    ]
}

files_for_testing = correct_licenses.keys()

@pytest.fixture
def licenses_from_records(shared_datadir):
    parsed_affiliations = {}
    for file in files_for_testing:
        parser = iop_parser.IOPParser()
        content=(shared_datadir / file).read_text()
        selector = Selector(text=content, type='xml')
        selector.remove_namespaces()
        affiliations = parser._get_license(selector)
        assert affiliations
        parsed_affiliations[os.path.basename(file)] = affiliations
    return parsed_affiliations


def test_country_in_OUP(licenses_from_records):
    for file_name in files_for_testing:
        assert len(licenses_from_records[file_name]) == len(correct_licenses[file_name])
        assert sorted(licenses_from_records[file_name]) == sorted(correct_licenses[file_name])
