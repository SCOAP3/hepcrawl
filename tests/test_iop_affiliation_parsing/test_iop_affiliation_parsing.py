import pytest

from hepcrawl.extractors import iop_parser
import os
from scrapy.selector import Selector

files_for_testing = ['2020_iop_abb4d6.xml',
                     '2021_iop_ac2a1d.xml', '2022_iop_ac3fa9.xml']
correct_affiliations = {files_for_testing[0]:
                        ['School of Physics and Electronic Engineering, Qilu Normal University, Jinan 250200, China',
                        'School of Physics and Electronic Engineering, Qilu Normal University, Jinan 250200, China',
                         'School of Physics and Electronic Engineering, Qilu Normal University, Jinan 250200, China',
                         'School of Physics and Electronic Engineering, Qilu Normal University, Jinan 250200, China',
                         'School of Physics and Electronic Engineering, Qilu Normal University, Jinan 250200, China',
                            'College of Physics and Space Science, China West Normal University, Nanchong 637002, China'],
                        files_for_testing[1]: [
                            'Department of Physics, North China Electric Power University, Baoding 071003, China',
                        'Department of Physics, North China Electric Power University, Baoding 071003, China'],
                        files_for_testing[2]: [
                            'School of Astronomy and Space Sciences, Nanjing University, Nanjing 210093, China',
                            'Key Laboratory of Particle Astrophysics, Institute of High Energy Physics, Chinese Academy of Sciences, Beijing 100049, China',
                            'Key Laboratory of Particle Astrophysics, Institute of High Energy Physics, Chinese Academy of Sciences, Beijing 100049, China',
                            'Key Laboratory of Particle Astrophysics, Institute of High Energy Physics, Chinese Academy of Sciences, Beijing 100049, China',
                            'INAF - Osservatorio Astrofisico di Torino, Strada Osservatorio 20, 10025 Pino Torinese (TO), Italy and INFN Sezione di Torino, Via P. Giuria 1, 10125 Torino, Italy',
                            'Key Laboratory for the Structure and Evolution of Celestial Objects, Yunnan Observatories, Chinese Academy of Sciences, Kunming 650011, China',
                            'Key Laboratory of Dark Matter and Space Astronomy, Purple Mountain Observatory, Chinese Academy of Sciences, Nanjing 210023, China']}


@pytest.fixture
def affiliations_from_records(shared_datadir):
    parsed_affiliations = {}
    for file in files_for_testing:
        parser = iop_parser.IOPParser()
        content=(shared_datadir / file).read_text()
        selector = Selector(text=content, type='xml')
        affiliations = parser._get_authors(selector)
        parsed_affiliations[os.path.basename(file)] = affiliations
    assert parsed_affiliations
    return parsed_affiliations


def test_country_in_IOP(affiliations_from_records):
    # article can have more than on aff
    for file_name in files_for_testing:
        affiliations_values = []
        for affiliations_from_a_record in affiliations_from_records[file_name]:
            # aff array
            for affiliation_value_from_record in affiliations_from_a_record['affiliations']:
                affiliations_values.append(
                    affiliation_value_from_record['value'])
        # checking, are values the same
        assert len(affiliations_values) == len(correct_affiliations[file_name])
        assert sorted(affiliations_values) == sorted(correct_affiliations[file_name])
