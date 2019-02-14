# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2016 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

from __future__ import absolute_import, print_function, unicode_literals

import pytest

from hepcrawl.spiders import hindawi_spider

from .responses import (
    fake_response_from_file,
    get_node,
)


@pytest.fixture
def records():
    """Return the results from the Hindawi spider."""

    parsed_records = []

    for file in ("hindawi/test_1.xml", "hindawi/test_2.xml"):
        spider = hindawi_spider.HindawiSpider()
        response = fake_response_from_file(file)
        nodes = get_node(spider, "//marc:record", response)

        parsed_records.append(spider.parse_node(response, nodes[0]))

    assert parsed_records
    return parsed_records


def test_title(records):
    """Test title."""
    titles = ("\u201cPi of the Sky\u201d Detector",
              "\u201cPi of the Sky\u201d Detector")

    for title, record in zip(titles, records):
        assert "title" in record
        assert record["title"] == title


def test_date_published(records):
    """Test date_published."""
    dates = ("2010-01-26", "2010-01-26")
    for date, record in zip(dates, records):
        assert "date_published" in record
        assert record["date_published"] == date


def test_authors(records):
    """Test authors."""
    excepted_data = (
        dict(authors=("Ma\u0142ek, Katarzyna", "Batsch, Tadeusz"),
             surnames=("Ma\u0142ek", "Batsch"),
             affiliations=(
                 "Center for Theoretical Physics Polish Academy of Sciences",
                 "The Andrzej Soltan Institute for Nuclear Studies"
             )),
        dict(authors=("Ma\u0142ek, Katarzyna", "Batsch, Tadeusz"),
             surnames=("Ma\u0142ek", "Batsch"),
             affiliations=(
                 "Center for Theoretical Physics Polish Academy of Sciences",
                 "The Andrzej Soltan Institute for Nuclear Studies"
             )),
    )

    for data, record in zip(excepted_data, records):
        assert 'authors' in record
        astr = record['authors']
        assert len(astr) == len(data['authors'])

        # make sure order is kept
        for index in range(len(data['authors'])):
            assert astr[index]['full_name'] == data['authors'][index]
            assert astr[index]['surname'] == data['surnames'][index]
            assert data['affiliations'][index] in [
                aff['value'] for aff in astr[index]['affiliations']
            ]


def test_source(records):
    """Test thesis source"""
    expected_data = ("Hindawi Publishing Corporation",
                     "Hindawi Publishing Corporation")

    for data, record in zip(expected_data, records):
        assert "source" in record
        assert record["source"] == "Hindawi Publishing Corporation"


def test_collections(records):
    """Test extracting collections."""
    collections = (['Advances in High Energy Physics'], ['Advances in High Energy Physics'])

    for collection, record in zip(collections, records):
        assert record["collections"]
        for r_collection in record["collections"]:
            assert r_collection["primary"] in collection


def test_copyright(records):
    """Test copyright."""
    cr_statements = ("Copyright \xa9 2010 Katarzyna Ma\u0142ek et al.",
                     "Copyright \xa9 2010 Katarzyna Ma\u0142ek et al.")

    for cr_statement, record in zip(cr_statements, records):
        assert "copyright_statement" in record
        assert "copyright_year" in record
        assert record["copyright_statement"] == cr_statement
        assert record["copyright_year"] == "2010"


def test_dois(records):
    """Test DOI."""
    dois = ("10.1155/2010/194946",
            "")

    for doi, record in zip(dois, records):
        if doi:
            assert "dois" in record
            assert record["dois"][0]["value"] == doi
        else:
            assert 'dois' not in record


def test_publication_info(records):
    """Test extracting journal data."""
    expected_results = (
        dict(journal_title="Advances in Astronomy",
             journal_year=2010,
             journal_issue="898351"),
        dict(journal_title="Advances in Astronomy",
             journal_year=2010,
             journal_issue="898351"),
    )

    for expected, record in zip(expected_results, records):
        for k, v in expected.items():
            assert k in record
            assert record[k] == v

def test_license(records):
    """Test extracting license information."""
    expected_licenses = (
        [{
            'license': 'CC-BY-3.0',
            'url': 'http://creativecommons.org/licenses/by/3.0/',
        }],
        [{
            'license': 'CC-BY-3.0',
            'url': 'http://creativecommons.org/licenses/by/3.0/',
        }]
    )

    for expected_license, record in zip(expected_licenses, records):
        assert 'license' in record
        assert record['license'] == expected_license


def test_page_nr(records):
    expected_results = (
        ['9'],
        ['9']
    )

    for expected, record in zip(expected_results, records):
        assert 'page_nr' in record
        assert record['page_nr'] == expected
