import pytest

from hepcrawl.extractors import oup_parser
import os

from scrapy.selector import Selector

correct_affiliations = {
    "2020_oup_ptaa186.xml": sorted([
        'Institute of Science and Engineering, , Shimane University, , Matsue 690-8504, , Japan',
        'Department of Physical Sciences, College of Science and Engineering, , Ritsumeikan University, , Shiga 525-8577, , Japan']),
    "2021_oup_ptab168.xml": sorted([
        "Center for Gravitational Physics, Yukawa Institute for Theoretical Physics, Kyoto University, Kyoto 606-8502, Japan",
        "Theoretical Research Division, Nishina Center, RIKEN, Saitama 351-0198, JapanInterdisciplinary Theoretical and Mathematical Sciences Program (iTHEMS), RIKEN Saitama 351-0198, Japan",
    ]),
    "2022_oup_ptac032.xml": sorted([
        "Institute of Science and Engineering, , Shimane University, , Matsue 690-8504, , Japan"]),
}

files_for_testing = correct_affiliations.keys()

@pytest.fixture
def affiliations_from_records(shared_datadir):
    parsed_affiliations = {}
    for file in files_for_testing:
        parser = oup_parser.OUPParser()
        content=(shared_datadir / file).read_text()
        selector = Selector(text=content, type='xml')
        affiliations = parser._get_authors(selector)
        parsed_affiliations[os.path.basename(file)] = affiliations
    assert parsed_affiliations
    return parsed_affiliations


def test_country_in_OUP(affiliations_from_records):
    print(affiliations_from_records, "HERE")
    for file_name in files_for_testing:
        affiliations_values = []
        for affiliations_from_record in affiliations_from_records[file_name]:
            print(affiliations_values, correct_affiliations[file_name], file_name)
            assert None
            # assert len(affiliations_values) == len(correct_affiliations[file_name])
            # assert sorted(affiliations_values) == correct_affiliations[file_name]