# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2019 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.
import shutil
from os import path

import pytest
from mock import patch

from scrapy.http import TextResponse

from .responses import fake_response_from_file

download_dir = '/tmp/oxford_test_download_dir/'


@pytest.fixture
def results():
    responses_dir = path.join(path.dirname(path.realpath(__file__)), 'responses')
    test_files = (
        '2019-01-18_19:30:31_ptep_iss_2019_1.img.zip',
        '2019-01-18_19:30:31_ptep_iss_2019_1.pdf.zip',
        '2019-01-18_19:30:31_ptep_iss_2019_1.xml.zip',
        '2019-01-18_19:30:31_ptep_iss_2019_1_archival.zip',
    )

    records = []
    with patch('hepcrawl.settings.OXFORD_DOWNLOAD_DIR', download_dir):
        from hepcrawl.spiders import oup_spider
        spider = oup_spider.OxfordUniversityPressSpider()

        for test_file in test_files:
            # copy files to download dir as they will be unzipped to their current directory
            test_file_path = path.join(responses_dir, 'oup', test_file)
            test_file_download_path = path.join(download_dir, test_file)
            shutil.copy2(test_file_path, test_file_download_path)

            # create response for downloaded package
            fake_response = fake_response_from_file(
                test_file_download_path,
                response_type=TextResponse,
                url='file://' + test_file_download_path
            )
            fake_response.meta['local'] = True

            # extract files from package and create response for xml files
            xml_requests = list(spider.handle_package_ftp(fake_response))
            xml_responses = []
            for req in xml_requests:
                xml_path = fake_response_from_file(req.meta['xml_url'].replace('file://', ''))
                xml_responses.append(xml_path)

            # parse records based on xml responses
            for response in xml_responses:
                records.extend(spider.parse(response))

    assert records
    yield records

    # delete all created data
    shutil.rmtree(download_dir, ignore_errors=True)


def test_extraction(results):
    """Test if all files were correctly extracted to the download dir from the packages."""
    expected_files_in_download_dir = (
        '2019-01-18_19:30:31_ptep_iss_2019_1/pdf/pty143.pdf',
        '2019-01-18_19:30:31_ptep_iss_2019_1/archival/pty143.pdf',
        '2019-01-18_19:30:31_ptep_iss_2019_1/pty143.xml',
    )

    for expected_file in expected_files_in_download_dir:
        assert path.exists(path.join(download_dir, expected_file))


def test_abstract(results):
    """Test extracting abstract."""
    abstracts = (
        "Abstract Regarding the significant interests in massive gravity and combining it with gravity\u2019s rainbow "
        "and also BTZ black holes, we apply the formalism introduced by Jiang and Han in order to investigate the quan"
        "tization of the entropy of black holes. We show that the entropy of BTZ black holes in massive gravity\u2019s"
        " rainbow is quantized with equally spaced spectra and it depends on the black holes\u2019 properties includin"
        "g massive parameters, electrical charge, the cosmological constant, and also rainbow functions. In addition, "
        "we show that quantization of the entropy results in the appearance of novel properties for this quantity, suc"
        "h as the existence of divergences, non-zero entropy in a vanishing horizon radius, and the possibility of tra"
        "cing out the effects of the black holes\u2019 properties. Such properties are absent in the non-quantized ver"
        "sion of the black hole entropy. Furthermore, we investigate the effects of quantization on the thermodynamica"
        "l behavior of the solutions. We confirm that due to quantization, novel phase transition points are introduce"
        "d and stable solutions are limited to only de Sitter black holes (anti-de Sitter and asymptotically flat solu"
        "tions are unstable).",
    )
    for abstract, record in zip(abstracts, results):
        if abstract:
            assert 'abstract' in record
            assert record['abstract'] == abstract
        else:
            assert 'abstract' not in record


def test_title(results):
    """Test extracting title."""
    titles = ("Entropy spectrum of charged BTZ black holes in massive gravity\u2019s rainbow",)
    for title, record in zip(titles, results):
        assert 'title' in record
        assert record['title'] == title


def test_date_published(results):
    """Test extracting date_published."""
    dates_published = ("2019-01-17",)
    for date_published, record in zip(dates_published, results):
        assert 'date_published' in record
        assert record['date_published'] == date_published


def test_license(results):
    """Test extracting license information."""
    expected_licenses = (
        [{
            'license': 'CC-BY-4.0',
            'url': 'http://creativecommons.org/licenses/by/4.0/',
        }],
    )
    for expected_license, record in zip(expected_licenses, results):
        assert 'license' in record
        assert record['license'] == expected_license


def test_dois(results):
    """Test extracting dois."""
    dois = ("10.1093/ptep/pty143",)
    for doi, record in zip(dois, results):
        assert 'dois' in record
        assert record['dois'][0]['value'] == doi
        break


def test_collections(results):
    """Test extracting collections."""
    collections = (['Progress of Theoretical and Experimental Physics'],)
    for collection, record in zip(collections, results):
        assert 'collections' in record
        for coll in collection:
            assert {"primary": coll} in record['collections']


def test_collaborations(results):
    """Test extracting collaboration."""
    collaborations = (
        [],
    )
    for collaboration, record in zip(collaborations, results):
        if collaboration:
            assert 'collaborations' in record
            assert record['collaborations'] == collaboration
        else:
            assert 'collaborations' not in record


def test_publication_info(results):
    """Test extracting dois."""
    expected_results = (
        dict(journal_title="Progress of Theoretical and Experimental Physics",
             journal_year=2019,
             journal_volume='2019',
             journal_issue='1',
             journal_artid='013E02'),
    )
    for expected, record in zip(expected_results, results):
        for k, v in list(expected.items()):
            assert k in record
            assert record[k] == v


def test_authors(results):
    """Test authors."""
    expected_results = (
        [
            {'affiliations': [{
                'value': 'Physics Department and Biruni Observatory, College of Sciences, Shiraz University, '
                         'Shiraz 71454, Iran'}],
                'surname': 'Panah',
                'given_names': 'B Eslam',
                'full_name': 'Panah, B Eslam',
                'email': 'beslampanah@shirazu.ac.ir'},
            {'affiliations': [{'value': 'Helmholtz-Institut Jena, Fr\xf6belstieg 3, Jena D-07743 Germany'}],
             'surname': 'Panahiyan',
             'given_names': 'S',
             'full_name': 'Panahiyan, S'},
            {'affiliations': [{'value': 'Physics Department and Biruni Observatory, College of Sciences, Shiraz '
                                        'University, Shiraz 71454, Iran'}],
             'surname': 'Hendi',
             'given_names': 'S H',
             'full_name': 'Hendi, S H'}],
    )

    for expected, record in zip(expected_results, results):
        assert 'authors' in record
        assert record['authors'] == expected


def test_copyrights(results):
    """Test extracting copyright."""
    expected_results = (
        dict(copyright_statement="\xa9  The Author(s) 2019. Published by Oxford University Press on behalf of the "
                              "Physical Society of Japan.",
             copyright_year="2019"),
    )
    for expected, record in zip(expected_results, results):
        for k, v in list(expected.items()):
            assert k in record
            assert record[k] == v


def test_doctype(results):
    expected_results = ('article', )

    for expected, record in zip(expected_results, results):
        assert 'journal_doctype' in record
        assert record['journal_doctype' ] == expected


def test_arxiv_eprints(results):
    """Text extracting arXiv eprints."""
    expected_results = (
        [dict(value='1611.10151')],
    )

    for expected, record in zip(expected_results, results):
        assert 'arxiv_eprints' in record
        assert record['arxiv_eprints'] == expected


def test_page_nr(results):
    expected_results = (
        [13],
    )

    for expected, record in zip(expected_results, results):
        assert 'page_nr' in record
        assert record['page_nr'] == expected
