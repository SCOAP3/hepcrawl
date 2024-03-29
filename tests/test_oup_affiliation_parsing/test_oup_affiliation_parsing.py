import pytest

from hepcrawl.extractors import oup_parser
import os

from scrapy.selector import Selector

correct_affiliations = {
    "2020_oup_ptaa186.xml": [
        {
            "affiliations": [
                {
                    "value": "Institute of Science and Engineering, Shimane University, Matsue 690-8504, Japan"
                }
            ],
            "surname": "Haba",
            "given_names": "Naoyuki",
        },
        {
            "affiliations": [
                {
                    "value": "Institute of Science and Engineering, Shimane University, Matsue 690-8504, Japan"
                },
                {
                    "value": "Department of Physical Sciences, College of Science and Engineering, Ritsumeikan University, Shiga 525-8577, Japan"
                },
            ],
            "surname": "Mimura",
            "given_names": "Yukihiro",
        },
        {
            "affiliations": [
                {
                    "value": "Institute of Science and Engineering, Shimane University, Matsue 690-8504, Japan"
                }
            ],
            "surname": "Yamada",
            "given_names": "Toshifumi",
            "email": "toshifumi@riko.shimane-u.ac.jp",
        },
    ],
    "2021_oup_ptab168.xml": [
        {
            "affiliations": [
                {
                    "value": "Center for Gravitational Physics, Yukawa Institute for Theoretical Physics, Kyoto University, Kyoto 606-8502, Japan"
                },
                {
                    "value": "Theoretical Research Division, Nishina Center, RIKEN, Saitama 351-0198, Japan"
                },
            ],
            "surname": "Aoki",
            "given_names": "Sinya",
            "email": "saoki@het.ph.tsukuba.ac.jp",
        },
        {
            "affiliations": [
                {
                    "value": "Interdisciplinary Theoretical and Mathematical Sciences Program (iTHEMS), RIKEN Saitama 351-0198, Japan"
                }
            ],
            "surname": "Yazaki",
            "given_names": "Koichi",
        },
    ],
    "2022_oup_ptac032.xml": [
        {
            "affiliations": [
                {
                    "value": "Department of Physics, Graduate School of Science, Osaka University, Toyonaka, Osaka 560-0043, Japan"
                }
            ],
            "surname": "Yamaguchi",
            "given_names": "Satoshi",
            "email": "yamaguch@het.phys.sci.osaka-u.ac.jp",
        }
    ],
}

files_for_testing = correct_affiliations.keys()

@pytest.fixture
def affiliations_from_records(shared_datadir):
    parsed_affiliations = {}
    for file in files_for_testing:
        parser = oup_parser.OUPParser()
        content=(shared_datadir / file).read_text()
        selector = Selector(text=content, type='xml')
        selector.remove_namespaces()
        affiliations = parser._get_authors(selector)
        assert affiliations
        parsed_affiliations[os.path.basename(file)] = affiliations
    return parsed_affiliations


def test_country_in_OUP(affiliations_from_records):
    for file_name in files_for_testing:
        assert len(affiliations_from_records[file_name]) == len(correct_affiliations[file_name])
        assert sorted(affiliations_from_records[file_name]) == sorted(correct_affiliations[file_name])
