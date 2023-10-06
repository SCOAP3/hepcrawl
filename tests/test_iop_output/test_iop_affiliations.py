import pytest

from hepcrawl.extractors import iop_parser
import os

from scrapy.selector import Selector

correct_affiliations = {
    "2021_iop_ac2a1d.xml": [
        {
            "affiliations": [
                {
                    "value": "Department of Physics, North China Electric Power University, Baoding 071003, China"
                }
            ],
            "surname": "Wang",
            "given_names": "Zhi-Gang",
            "email": "zgwang@aliyun.com",
        },
        {
            "affiliations": [
                {
                    "value": "Department of Physics, North China Electric Power University, Baoding 071003, China"
                }
            ],
            "surname": "Xin",
            "given_names": "Qi",
        },
    ],
    "2022_iop_ac3fa9.xml": [
        {
            "affiliations": [
                {
                    "value": "School of Astronomy and Space Sciences, Nanjing University, Nanjing 210093, China"
                }
            ],
            "surname": "Wang",
            "given_names": "Xiang-Yu",
            "email": "xywang@nju.edu.cn",
        },
        {
            "affiliations": [
                {
                    "value": "Key Laboratory of Particle Astrophysics, Institute of High Energy Physics, Chinese Academy of Sciences, Beijing 100049, China"
                }
            ],
            "surname": "Bi",
            "given_names": "Xiao-Jun",
        },
        {
            "affiliations": [
                {
                    "value": "Key Laboratory of Particle Astrophysics, Institute of High Energy Physics, Chinese Academy of Sciences, Beijing 100049, China"
                }
            ],
            "surname": "Cao",
            "given_names": "Zhen",
        },
        {
            "affiliations": [
                {
                    "value": "INAF - Osservatorio Astrofisico di Torino, Strada Osservatorio 20, 10025 Pino Torinese (TO), Italy and INFN Sezione di Torino, Via P. Giuria 1, 10125 Torino, Italy"
                }
            ],
            "surname": "Vallania",
            "given_names": "Piero",
        },
        {
            "affiliations": [
                {
                    "value": "Key Laboratory of Particle Astrophysics, Institute of High Energy Physics, Chinese Academy of Sciences, Beijing 100049, China"
                }
            ],
            "surname": "Wu",
            "given_names": "Han-Rong",
        },
        {
            "affiliations": [
                {
                    "value": "Key Laboratory for the Structure and Evolution of Celestial Objects, Yunnan Observatories, Chinese Academy of Sciences, Kunming 650011, China"
                }
            ],
            "surname": "Yan",
            "given_names": "Da-Hai",
        },
        {
            "affiliations": [
                {
                    "value": "Key Laboratory of Dark Matter and Space Astronomy, Purple Mountain Observatory, Chinese Academy of Sciences, Nanjing 210023, China"
                }
            ],
            "surname": "Yuan",
            "given_names": "Qiang",
        },
    ],
    "2020_iop_abb4d6.xml": [
        {
            "affiliations": [
                {
                    "value": "School of Physics and Electronic Engineering, Qilu Normal University, Jinan 250200, China"
                }
            ],
            "surname": "Sha",
            "given_names": "Bei",
        },
        {
            "affiliations": [
                {
                    "value": "School of Physics and Electronic Engineering, Qilu Normal University, Jinan 250200, China"
                }
            ],
            "surname": "Liu",
            "given_names": "Zhi-E",
        },
        {
            "affiliations": [
                {
                    "value": "School of Physics and Electronic Engineering, Qilu Normal University, Jinan 250200, China"
                }
            ],
            "surname": "Liu",
            "given_names": "Yu-Zhen",
        },
        {
            "affiliations": [
                {
                    "value": "School of Physics and Electronic Engineering, Qilu Normal University, Jinan 250200, China"
                }
            ],
            "surname": "Tan",
            "given_names": "Xia",
        },
        {
            "affiliations": [
                {
                    "value": "School of Physics and Electronic Engineering, Qilu Normal University, Jinan 250200, China"
                }
            ],
            "surname": "Zhang",
            "given_names": "Jie",
        },
        {
            "affiliations": [
                {
                    "value": "College of Physics and Space Science, China West Normal University, Nanchong 637002, China"
                }
            ],
            "surname": "Yang",
            "given_names": "Shu-Zheng",
        },
    ],
}


files_for_testing = correct_affiliations.keys()

@pytest.fixture
def affiliations_from_records(shared_datadir):
    parsed_affiliations = {}
    for file in files_for_testing:
        parser = iop_parser.IOPParser()
        content=(shared_datadir / file).read_text()
        selector = Selector(text=content, type='xml')
        selector.remove_namespaces()
        affiliations = parser._get_authors(selector)
        assert affiliations
        parsed_affiliations[os.path.basename(file)] = affiliations
    return parsed_affiliations


def test_affiliations_in_IOP(affiliations_from_records):
    for file_name in files_for_testing:
        assert len(affiliations_from_records[file_name]) == len(correct_affiliations[file_name])
        assert sorted(affiliations_from_records[file_name]) == sorted(correct_affiliations[file_name])
