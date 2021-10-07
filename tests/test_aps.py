# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2015, 2016 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.



import pytest

from scrapy.http import TextResponse
from hepcrawl.spiders import aps_spider
from .responses import fake_response_from_file


@pytest.fixture
def results():
    """Return results generator from the APS spider."""

    records = []

    for file in ('aps/aps_single_response.json',):
        fake_response = fake_response_from_file(
            file,
            response_type=TextResponse,
        )
        spider = aps_spider.APSSpider()
        records.extend(list(spider.parse(fake_response)))

    assert records
    assert len(records) == 1

    return records


def test_abstract(results):
    """Test extracting abstract."""
    abstracts = (
        "We use a popular fictional disease, zombies, in order to introduce techniques used in modern epidemiology"
        " modeling, and ideas and techniques used in the numerical study of critical phenomena. We consider variants of"
        " zombie models, from fully connected continuous time dynamics to a full scale exact stochastic dynamic"
        " simulation of a zombie outbreak on the continental United States. Along the way, we offer a closed form"
        " analytical expression for the fully connected differential equation, and demonstrate that the single person"
        " per site two dimensional square lattice version of zombies lies in the percolation universality class. We end"
        " with a quantitative study of the full scale US outbreak, including the average susceptibility of different"
        " geographical regions.",
    )
    for abstract, record in zip(abstracts, results):
        if abstract:
            assert 'abstract' in record
            assert record['abstract'] == abstract
        else:
            assert 'abstract' not in record


def test_title(results):
    """Test extracting title."""
    titles = ("You can run, you can hide: The epidemiology and statistical mechanics of zombies",)
    for title, record in zip(titles, results):
        assert 'title' in record
        assert record['title'] == title


def test_date_published(results):
    """Test extracting date_published."""
    dates_published = ("2015-11-02",)
    for date_published, record in zip(dates_published, results):
        assert 'date_published' in record
        assert record['date_published'] == date_published


def test_page_nr(results):
    """Test extracting page_nr"""
    page_nrs = [[11],]
    for page_nr, record in zip(page_nrs, results):
        assert 'page_nr' in record
        assert record['page_nr'] == page_nr


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
    dois = ("10.1103/PhysRevE.92.052801", )
    for doi, record in zip(dois, results):
        assert 'dois' in record
        assert record['dois'][0]['value'] == doi
        break


def test_collections(results):
    """Test extracting collections."""
    collections = [['HEP', 'Citeable', 'Published']]
    for collection, record in zip(collections, results):
        assert 'collections' in record
        for coll in collection:
            assert {"primary": coll} in record['collections']


def test_collaborations(results):
    """Test extracting collaboration."""
    collaborations = [
        [{"value": "OSQAR Collaboration"}],
    ]
    for collaboration, record in zip(collaborations, results):
        assert 'collaborations' in record
        assert record['collaborations'] == collaboration


def test_subjects(results):
    """Test extracting collaboration."""
    subjects = [
        [{
            'scheme': 'APS',
            'source': '',
            'term': 'Quantum Information',
        }],
    ]
    for subject, record in zip(subjects, results):
        assert 'field_categories' in record
        assert record['field_categories'] == subject


def test_publication_info(results):
    """Test extracting dois."""
    expected_results = (
        dict(journal_title="Physical Review E",
             journal_year=2015,
             journal_volume="92",
             journal_issue="5"),
    )
    for expected, record in zip(expected_results, results):
        for k, v in list(expected.items()):
            assert k in record
            assert record[k] == v


def test_authors(results):
    """Test authors."""
    expected_results = (
        dict(
            affiliation='Laboratory of Atomic and Solid State Physics, Cornell University, Ithaca, New York 14853, USA',
            author_full_names=['Alemi, Alexander A.', 'Bierbaum, Matthew', 'Myers, Christopher R.', 'Sethna, James P.']
        ),
    )
    for expected, record in zip(expected_results, results):
        assert 'authors' in record
        assert len(record['authors']) == len(expected['author_full_names'])

        record_full_names = [author['full_name'] for author in record['authors']]
        assert set(expected['author_full_names']) == set(record_full_names)  # assert that we have the same list of authors
        for author in record['authors']:
            assert author['affiliations'][0]['value'] == expected['affiliation']


def test_copyrights(results):
    """Test extracting copyright."""
    expected_results = (
        dict(copyright_holder="authors",
             copyright_year="2015",
             copyright_statement="Published by the American Physical Society"),
    )
    for expected, record in zip(expected_results, results):
        for k, v in list(expected.items()):
            assert k in record
            assert record[k] == v


def test_arxiv_eprints(results):
    expected_results = (
        [{'value': '1806.06486'}],
    )

    for expected, record in zip(expected_results, results):
        assert 'arxiv_eprints' in record
        assert record['arxiv_eprints'] == expected


def test_doctype(results):
    expected_results = (
        'article',
    )

    for expected, record in zip(expected_results, results):
        assert 'journal_doctype' in record
        assert record['journal_doctype'] == expected
