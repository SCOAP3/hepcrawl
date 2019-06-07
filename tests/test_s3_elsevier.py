# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2015, 2016 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.
from freezegun import freeze_time
import shutil
from os import path, makedirs

import pytest
from mock import patch

from scrapy.http import TextResponse

from .responses import fake_response_from_file


@pytest.fixture
def results():
    """Return results generator from the Elsevier spider."""
    download_dir = '/tmp/elsevier_test_download_dir/'
    unpack_dir = '/tmp/elsevier_test_unpack_dir/'
    test_files = ('CERNR000000005008A.tar', 'CERNAB00000005657_stripped.tar', 'vtex00403986_a-2b_partial_simple.zip')

    with patch('hepcrawl.settings.ELSEVIER_DOWNLOAD_DIR', download_dir),\
         patch('hepcrawl.settings.ELSEVIER_UNPACK_FOLDER', unpack_dir), \
         freeze_time("2019-03-27"):
            from hepcrawl.spiders import s3_elsevier_spider
            records = []

            for test_file in test_files:
                # create unpack path if not created automatically
                if not path.exists(unpack_dir):
                    makedirs(unpack_dir)

                fake_response = fake_response_from_file(
                    path.join('s3_elsevier', test_file),
                    response_type=TextResponse,
                    url='http://example.com/' + test_file
                )
                fake_response.meta['local_filename'] = path.join(download_dir, test_file)

                spider = s3_elsevier_spider.S3ElsevierSpider()
                records.extend(list(spider.handle_package(fake_response)))

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

        u"The quantization of black hole parameters is a long-standing topic in physics. Adiabatic invariance, "
        u"periodicity of outgoing waves, quantum tunneling, and quasi-normal modes are the typical tools via which the "
        u"area and the entropy of a black hole are quantized. In this paper, the quantum spectra of area and entropy of "
        u"quantum-corrected Schwarzschild black hole are investigated. The deformation in the space\u2013time of "
        u"Schwarzschild black hole was perused by Kazakov and Solodukhin. Here the deformed Schwarzschild metric is "
        u"taken into account, and the effect of the space\u2013time modification on the minimal area and entropy "
        u"increment for the Schwarzschild black hole is scrutinized, utilizing two different procedure: Jiang-Han's "
        u"method of the adiabatic invariant integral and Zeng et al.'s approach of the periodic property of outgoing "
        u"waves. The analyses of this paper draw the conclusion that the quantum correction to the space\u2013time does "
        u"not alter the quantum characteristics of the Schwarzschild black hole.",

        "<math><mi>N</mi><mo>=</mo><mn>3</mn></math> Weyl multiplet in four dimensions was first constructed in J. van "
        "Muiden et al. (2017) where the authors used the current multiplet approach to obtain the linearized transforma"
        "tion rules and completed the non-linear variations using the superconformal algebra. The multiplet of currents"
        " was obtained by a truncation of the multiplet of currents for the <math><mi>N</mi><mo>=</mo><mn>4</mn></math>"
        " vector multiplet. While the procedure seems to be correct, the result suffers from several inconsistencies. T"
        "he inconsistencies are observed in the transformation rules as well as the field dependent structure constants"
        " in the corresponding soft algebra. We take a different approach, and compute the transformation rule as well "
        "as the corresponding soft algebra by demanding consistency."
    )
    for abstract, record in zip(abstracts, results):
        if abstract:
            assert 'abstract' in record
            assert record['abstract'] == abstract
        else:
            assert 'abstract' not in record


def test_title(results):
    """Test extracting title."""
    titles = (u"Renormalization in condensed matter: Fermionic systems \u2013 from mathematics to materials",
              "Spectroscopy of quantum-corrected Schwarzschild black hole",
              u"Comment on \u201cThe Weyl multiplet in four dimensions\u201d")
    for title, record in zip(titles, results):
        assert 'title' in record
        assert record['title'] == title


def test_date_published(results):
    """Test extracting date_published."""
    dates_published = ("2018-07-04",
                       "2019-01-18",
                       "2019-03-27")
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
        [{
            'license': 'CC-BY-3.0',
            'url': 'http://creativecommons.org/licenses/by/3.0/'
        }],
        [{
            'license': 'CC-BY-3.0',
            'url': 'http://creativecommons.org/licenses/by/3.0/'
        }],
    )
    for expected_license, record in zip(expected_licenses, results):
        assert 'license' in record
        assert record['license'] == expected_license


def test_dois(results):
    """Test extracting dois."""
    dois = ("10.1016/j.nuclphysb.2018.07.004",
            "10.1016/j.nuclphysb.2019.01.010",
            "10.1016/j.physletb.2018.12.072")
    for doi, record in zip(dois, results):
        assert 'dois' in record
        assert record['dois'][0]['value'] == doi
        break


def test_collections(results):
    """Test extracting collections."""
    collections = (['Nuclear Physics B'],
                   ['Nuclear Physics B'],
                   ['Physics Letters B'])
    for collection, record in zip(collections, results):
        assert 'collections' in record
        for coll in collection:
            assert {"primary": coll} in record['collections']


def test_collaborations(results):
    """Test extracting collaboration."""
    collaborations = (
        [],
        [],
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
             journal_year=2018,
             journal_artid='14394',
             journal_doctype='article'),
        dict(journal_title="Nuclear Physics B",
             journal_volume='940 C',
             journal_year=2019,
             journal_artid='14550',
             journal_doctype='article'),
        dict(journal_title="Physics Letters B",
             journal_volume='791 C',
             journal_year=2019,
             journal_artid='34445'),
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
        [{'affiliations': [{'value': 'Department of Mathematics, Shahjalal University of Science and Technology, '
                                     'Sylhet-3114, Bangladesh'}],
          'email': 'jalal.ndc@gmail.com',
          'full_name': 'Shahjalal, Md.',
          'given_names': 'Md.',
          'surname': 'Shahjalal'}],
        [{"surname": "Hegde",
          "given_names": "Subramanya",
          "affiliations": [{
                               "value": "Indian Institute of Science Education and Research Thiruvananthapuram, "
                                        "Vithura, Kerala, 695551, India"}
                           ],
          "full_name": "Hegde, Subramanya",
          "orcid": "ORCID:0000-0002-0666-0785",
          "email": "smhegde14@iisertvm.ac.in"},
         {"affiliations": [{
                               "value": "Indian Institute of Science Education and Research Thiruvananthapuram, "
                                        "Vithura, Kerala, 695551, India"}],
          "surname": "Sahoo",
          "given_names": "Bindusar",
          "full_name": "Sahoo, Bindusar"
          }]
    )

    for expected, record in zip(expected_results, results):
        assert 'authors' in record
        assert record['authors'] == expected


def test_copyrights(results):
    """Test extracting copyright."""
    expected_results = (
        dict(copyright_holder="The Author",
             copyright_year="2018",
             copyright_statement="The Author"),
        dict(copyright_holder="The Author(s)",
             copyright_year="2019",
             copyright_statement="The Author(s)"),
        dict(copyright_holder="The Authors",
             copyright_year="2019",
             copyright_statement="The Authors"),
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
        [
            {'value': {
                'path': '/CERNAB00000005657_stripped/05503213/v940sC/S0550321319300124/main.xml',
                'filetype': 'xml'}},
            {'value': {
                'path': '/CERNAB00000005657_stripped/05503213/v940sC/S0550321319300124/main.pdf',
                'filetype': 'pdf'}}
        ],
        [
            {"value": {
                "path": "/vtex00403986_a-2b_partial_simple/03702693/v791sC/S0370269319301078/main.xml",
                "filetype": "xml"}},
            {"value": {
                "path": "/vtex00403986_a-2b_partial_simple/03702693/v791sC/S0370269319301078/main.pdf",
                "filetype": "pdf"}},
            {"value": {
                "path": "/vtex00403986_a-2b_partial_simple/03702693/v791sC/S0370269319301078/main_a-2b.pdf",
                "filetype": "pdfa"}
            }
        ]
    )

    for expected, record in zip(expected_results, results):
        assert len(expected) == len(record['local_files'])

        for expected_file, record_file in zip(expected, record['local_files']):
            assert record_file['value']['filetype'] == expected_file['value']['filetype']
            assert expected_file['value']['path'] in record_file['value']['path']


def test_docsubtype(results):
    expected_results = (
        'article',
        'article',
        'other'
    )

    for expected, record in zip(expected_results, results):
        assert 'journal_doctype' in record
        assert record['journal_doctype'] == expected


def test_page_nr(results):
    expected_results = (
        [],
        [9],
        [4]
    )

    for expected, record in zip(expected_results, results):
        if expected:
            assert 'page_nr' in record
            assert record['page_nr'] == expected
        else:
            assert 'page_nr' not in record
