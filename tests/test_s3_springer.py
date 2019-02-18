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
    download_dir = '/tmp/springer_test_download_dir/'
    unpack_dir = '/tmp/springer_test_unpack_dir/'
    test_files = ('ftp_PUB_19-01-29_20-02-10_JHEP.zip', 'ftp_PUB_19-01-29_20-02-10_EPJC.zip',
                  'ftp_PUB_19-02-06_16-01-13_EPJC_stripped.zip')
    responses_dir = path.join(path.dirname(path.realpath(__file__)), 'responses')

    records = []

    with patch('hepcrawl.settings.SPRINGER_DOWNLOAD_DIR', download_dir),\
         patch('hepcrawl.settings.SPRINGER_UNPACK_FOLDER', unpack_dir):
            for test_file in test_files:

                if not path.exists(unpack_dir):
                    makedirs(unpack_dir)

                # create response for downloaded package
                test_file_path = path.join(responses_dir, 's3_springer', test_file)
                fake_response = fake_response_from_file(
                    test_file_path,
                    response_type=TextResponse,
                    url='http://example.com/' + test_file
                )
                fake_response.meta['ftp_local_filename'] = test_file_path

                from hepcrawl.spiders import s3_springer_spider
                spider = s3_springer_spider.S3SpringerSpider()

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
    shutil.rmtree(unpack_dir, ignore_errors=True)


def test_abstract(results):
    """Test extracting abstract."""
    abstracts = (
        "It was known that quantum curves and super Chern-Simons matrix models correspond to each other. From the "
        "viewpoint of symmetry, the algebraic curve of genus one, called the del Pezzo curve, enjoys symmetry of the "
        "exceptional algebra, while the super Chern-Simons matrix model is described by the free energy of topological "
        "strings on the del Pezzo background with the symmetry broken. We study the symmetry breaking of the quantum "
        "cousin of the algebraic curve and reproduce the results in the super Chern-Simons matrix model.",

        "We discuss in detail the distributions of energy, radial pressure and tangential pressure inside the nucleon. "
        "In particular, this discussion is carried on in both the instant form and the front form of dynamics. Moreover "
        "we show for the first time how these mechanical concepts can be defined when the average nucleon momentum does "
        "not vanish. We express the conditions of hydrostatic equilibrium and stability in terms of these two and "
        "three-dimensional energy and pressure distributions. We briefly discuss the phenomenological relevance of our"
        " findings with a simple yet realistic model. In the light of this exhaustive mechanical description of the "
        "nucleon, we also present several possible connections between hadronic physics and compact stars, like e.g. "
        "the study of the equation of state for matter under extreme conditions and stability constraints.",

        u"This paper describes a strategy for a general search used by the ATLAS Collaboration to find potential "
        u"indications of new physics. Events are classified according to their final state into many event classes. For "
        u"each event class an automated search algorithm tests whether the data are compatible with the Monte Carlo "
        u"simulated expectation in several distributions sensitive to the effects of new physics. The significance of a "
        u"deviation is quantified using pseudo-experiments. A data selection with a significant deviation defines a "
        u"signal region for a dedicated follow-up analysis with an improved background expectation. The analysis of the "
        u"data-derived signal regions on a new dataset allows a statistical interpretation without the large "
        u"look-elsewhere effect. The sensitivity of the approach is discussed using Standard Model processes and "
        u"benchmark signals of new physics. As an example, results are shown for 3.2 fb$$^{-1}$$ <math><msup><mrow>"
        u"</mrow><mrow><mo>-</mo><mn>1</mn></mrow></msup></math>  of proton\u2013proton collision data at a "
        u"centre-of-mass energy of 13 $$\\text {TeV}$$ <math><mtext>TeV</mtext></math>  collected with the ATLAS "
        u"detector at the LHC in 2015, in which more than 700 event classes and more than $$10^5$$ <math><msup><mn>10"
        u"</mn><mn>5</mn></msup></math>  regions have been analysed. No significant deviations are found and "
        u"consequently no data-derived signal regions for a follow-up analysis have been defined."
    )
    for abstract, record in zip(abstracts, results):
        if abstract:
            assert 'abstract' in record
            assert record['abstract'] == abstract
        else:
            assert 'abstract' not in record


def test_title(results):
    """Test extracting title."""
    titles = ("Symmetry breaking in quantum curves and super Chern-Simons matrix models",
              "Revisiting the mechanical properties of the nucleon",

              "A strategy for a general search for new phenomena using data-derived signal regions and its "
              "application within the ATLAS experiment")
    for title, record in zip(titles, results):
        assert 'title' in record
        assert record['title'] == title


def test_date_published(results):
    """Test extracting date_published."""
    dates_published = ("2019-01-28",
                       "2019-01-29",
                       "2019-02-06")
    for date_published, record in zip(dates_published, results):
        assert 'date_published' in record
        assert record['date_published'] == date_published


def test_license(results):
    """Test extracting license information."""
    expected_licenses = (
        [{
            'license': 'CC-BY-3.0',
            'url': 'https://creativecommons.org/licenses/by/3.0',
        }],
        [{
            'license': 'CC-BY-4.0',
            'url': 'https://creativecommons.org/licenses//by/4.0',
        }],
        [{
            'license': 'CC-BY-4.0',
            'url': 'https://creativecommons.org/licenses//by/4.0',
        }],
    )
    for expected_license, record in zip(expected_licenses, results):
        assert 'license' in record
        assert record['license'] == expected_license


def test_dois(results):
    """Test extracting dois."""
    dois = ("10.1007/JHEP01(2019)210",
            "10.1140/epjc/s10052-019-6572-3",
            "10.1140/epjc/s10052-019-6540-y")
    for doi, record in zip(dois, results):
        assert 'dois' in record
        assert record['dois'][0]['value'] == doi
        break


def test_collections(results):
    """Test extracting collections."""
    collections = (['Journal of High Energy Physics'],
                   ['European Physical Journal C'],
                   ['European Physical Journal C'])
    for collection, record in zip(collections, results):
        assert 'collections' in record
        for coll in collection:
            assert {"primary": coll} in record['collections']


def test_collaborations(results):
    """Test extracting collaboration."""
    collaborations = (
        [],
        [],
        [{'value': 'ATLAS Collaboration'}]
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
        dict(journal_title="Journal of High Energy Physics",
             journal_year=2019,
             journal_volume='2019',
             journal_issue='1',
             journal_fpage='1',
             journal_lpage='29',
             journal_artid='JHEP012019210'),
        dict(journal_title="European Physical Journal C",
             journal_year=2019,
             journal_volume='79',
             journal_issue='1',
             journal_fpage='1',
             journal_lpage='25',
             journal_artid='s10052-019-6572-3'),
        dict(journal_title="European Physical Journal C",
             journal_year=2019,
             journal_volume='79',
             journal_issue='2',
             journal_fpage='1',
             journal_lpage='45',
             journal_artid='s10052-019-6540-y'),
    )
    for expected, record in zip(expected_results, results):
        for k, v in expected.items():
            assert k in record
            assert record[k] == v


def test_authors(results):
    """Test authors."""
    expected_results = (
        [
            {"affiliations": [{"organization": "Kyoto University",
                               "value": "Center for Gravitational Physics, Yukawa Institute for Theoretical Physics, "
                                        "Kyoto University, Sakyo-ku, Kyoto, 606-8502, Japan",
                               "country": "Japan"}],
             "surname": "Kubo",
             "given_names": "Naotaka",
             "full_name": "Kubo, Naotaka",
             "email": "naotaka.kubo@yukawa.kyoto-u.ac.jp"},
            {"affiliations": [
                {"organization": "Osaka City University",
                 "value": "Department of Physics, Graduate School of Science, Osaka City University, Sumiyoshi-ku, "
                          "Osaka, 558-8585, Japan",
                 "country": "Japan"},
                {"organization": "Nambu Yoichiro Institute of Theoretical and Experimental Physics (NITEP)",
                 "value": "Nambu Yoichiro Institute of Theoretical and Experimental Physics (NITEP), Sumiyoshi-ku, "
                          "Osaka, 558-8585, Japan",
                 "country": "Japan"},
                {"organization": "Osaka City University Advanced Mathematical Institute (OCAMI)",
                 "value": "Osaka City University Advanced Mathematical Institute (OCAMI), "
                          "Sumiyoshi-ku, Osaka, 558-8585, Japan",
                 "country": "Japan"}],
                "surname": "Moriyama",
                "given_names": "Sanefumi",
                "full_name": "Moriyama, Sanefumi",
                "email": "moriyama@sci.osaka-cu.ac.jp"},
            {"affiliations": [{"organization": "School of Physics, Korea Institute for Advanced Study",
                               "value": "School of Physics, Korea Institute for Advanced Study, Dongdaemun-gu, Seoul, 02455, Korea",
                               "country": "Korea"}], "surname": "Nosaka", "given_names": "Tomoki",
             "full_name": "Nosaka, Tomoki",
             "email": "nosaka@yukawa.kyoto-u.ac.jp"}],
        [
            {"affiliations": [{"organization": u"Universit\u00e9 Paris-Saclay",
                               "value": u"Centre de Physique Th\u00e9orique, \u00c9cole polytechnique, CNRS, "
                                        u"Universit\u00e9 Paris-Saclay, Palaiseau, 91128, France",
                               "country": "France"}],
             "surname": u"Lorc\u00e9",
             "given_names": u"C\u00e9dric",
             "full_name": u"Lorc\u00e9, C\u00e9dric",
             "email": ""},
            {"affiliations": [{"organization": u"Universit\u00e9 Paris-Saclay",
                               "value": u"IRFU, CEA, Universit\u00e9 Paris-Saclay, Gif-sur-Yvette, 91191, France",
                               "country": "France"}],
             "surname": "Moutarde",
             "given_names": u"Herv\u00e9",
             "full_name": u"Moutarde, Herv\u00e9",
             "email": ""},
            {"affiliations": [{"organization": u"Universit\u00e9 Paris-Saclay",
                               "value": u"Centre de Physique Th\u00e9orique, \u00c9cole polytechnique, CNRS, "
                                        u"Universit\u00e9 Paris-Saclay, Palaiseau, 91128, France",
                               "country": "France"},
                              {"organization": u"Universit\u00e9 Paris-Saclay",
                               "value": u"IRFU, CEA, Universit\u00e9 Paris-Saclay, Gif-sur-Yvette, 91191, France",
                               "country": "France"}],
             "surname": u"Trawi\u0144ski",
             "given_names": "Arkadiusz",
             "full_name": u"Trawi\u0144ski, Arkadiusz",
             "email": "Arkadiusz.Trawinski@cea.fr"}]

    )

    for expected, record in zip(expected_results, results):
        assert 'authors' in record
        assert record['authors'] == expected


def test_page_nr(results):
    """Test extracting copyright."""
    expected_results = (
        [29],
        [25],
        [45]
    )
    for expected, record in zip(expected_results, results):
        assert 'page_nr' in record
        assert record['page_nr'] == expected


def test_copyrights(results):
    """Test extracting copyright."""
    expected_results = (
        dict(copyright_holder="SISSA, Trieste, Italy",
             copyright_year="2019"),
        dict(copyright_holder="The Author(s)",
             copyright_year="2019"),
        dict(copyright_holder='CERN for the benefit of the ATLAS collaboration',
             copyright_year='2019')
    )
    for expected, record in zip(expected_results, results):
        for k, v in expected.items():
            assert k in record
            assert record[k] == v


def test_arxiv(results):
    """Text extracting arXiv eprints."""
    expected_results = (
        [dict(value='1811.06048')],
        [dict(value='1810.09837')],
        [dict(value='1807.07447v1')],
    )

    for expected, record in zip(expected_results, results):
        assert 'arxiv_eprints' in record
        assert record['arxiv_eprints'] == expected


def test_doctype(results):
    expected_results = (
        'publication',
        'publication',
        'publication',
    )

    for expected, record in zip(expected_results, results):
        assert 'journal_doctype' in record
        assert record['journal_doctype'] == expected
