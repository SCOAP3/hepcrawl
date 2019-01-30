# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2015, 2016 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.
import shutil
from os import path, makedirs

import pytest
from mock import patch

from scrapy.http import TextResponse

from .responses import fake_response_from_file


@pytest.fixture
def results():
    """Return results generator from the WSP spider."""
    download_dir = '/tmp/elsevier_test_download_dir/'
    unpack_dir = '/tmp/elsevier_test_unpack_dir/'
    test_file = 'CERNR000000005008A.tar'

    with patch('hepcrawl.settings.ELSEVIER_DOWNLOAD_DIR', download_dir):
        with patch('hepcrawl.settings.ELSEVIER_UNPACK_FOLDER', unpack_dir):
            # unpack path is not created automatically
            if not path.exists(unpack_dir):
                makedirs(unpack_dir)

            from hepcrawl.spiders import s3_elsevier_spider

            fake_response = fake_response_from_file(
                path.join('s3_elsevier', test_file),
                response_type=TextResponse,
                url='http://example.com/' + test_file
            )
            fake_response.meta['local_filename'] = path.join(download_dir, test_file)

            spider = s3_elsevier_spider.S3ElsevierSpider()
            records = list(spider.handle_package(fake_response))

            assert records
            yield records

    shutil.rmtree(download_dir, ignore_errors=True)
    shutil.rmtree(unpack_dir, ignore_errors=True)


def test_abstract(results):
    """Test extracting abstract."""
    abstracts = (
        "Renormalization plays an important role in the theoretically and mathematically careful analysis of models in "
        "condensed-matter physics. I review selected results about correlated-fermion systems, ranging from "
        "mathematical theorems to applications in models relevant for materials science, such as the prediction of "
        "equilibrium phases of systems with competing ordering tendencies, and quantum criticality.",
    )
    for abstract, record in zip(abstracts, results):
        if abstract:
            assert 'abstract' in record
            assert record['abstract'] == abstract
        else:
            assert 'abstract' not in record


def test_title(results):
    """Test extracting title."""
    titles = (u"Renormalization in condensed matter: Fermionic systems \u2013 from mathematics to materials",)
    for title, record in zip(titles, results):
        assert 'title' in record
        assert record['title'] == title


def test_date_published(results):
    """Test extracting date_published."""
    dates_published = ("2018-07-04",)
    for date_published, record in zip(dates_published, results):
        assert 'date_published' in record
        assert record['date_published'] == date_published


def test_license(results):
    """Test extracting license information."""
    expected_licenses = (
        [{
            'license': 'CC-BY-3.0',
            'url': 'http://creativecommons.org/licenses/by/3.0/',
        }],
    )
    for expected_license, record in zip(expected_licenses, results):
        assert 'license' in record
        assert record['license'] == expected_license


def test_dois(results):
    """Test extracting dois."""
    dois = ("10.1016/j.nuclphysb.2018.07.004",)
    for doi, record in zip(dois, results):
        assert 'dois' in record
        assert record['dois'][0]['value'] == doi
        break


def test_collections(results):
    """Test extracting collections."""
    collections = (['Nuclear Physics B'],)
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
        dict(journal_title="Nuclear Physics B",
             journal_year=2019,
             journal_artid='14394'),
    )
    for expected, record in zip(expected_results, results):
        for k, v in expected.items():
            assert k in record
            assert record[k] == v


def test_authors(results):
    """Test authors."""
    expected_results = (
        [{'affiliations': [{'value': u'Institut f\xfcr Theoretische Physik, Universit\xe4t Heidelberg, '
                                     u'Philosophenweg 19, 69120 Heidelberg, Germany'}],
          'email': 'salmhofer@uni-heidelberg.de',
          'full_name': 'Salmhofer, Manfred',
          'given_names': 'Manfred',
          'surname': 'Salmhofer'}],
    )

    for expected, record in zip(expected_results, results):
        assert 'authors' in record
        assert record['authors'] == expected


def test_copyrights(results):
    """Test extracting copyright."""
    expected_results = (
        dict(copyright_holder="The Author",
             copyright_year="2018",
             copyright_statement="The Author",
             copyright_material="Article"),
    )
    for expected, record in zip(expected_results, results):
        for k, v in expected.items():
            assert k in record
            assert record[k] == v


def test_files(results):
    expected_results = (
        [
            {'value': {
                'path': '/CERNR000000005008/S0550321318301901/main.xml',
                'filetype': 'xml'}},
            {'value': {
                'path': '/CERNR000000005008/S0550321318301901/main.pdf',
                'filetype': 'pdf'}}
        ],
    )

    for expected, record in zip(expected_results, results):
        assert len(expected) == len(record['local_files'])

        for expected_file, record_file in zip(expected, record['local_files']):
            assert record_file['value']['filetype'] == expected_file['value']['filetype']
            assert expected_file['value']['path'] in record_file['value']['path']
