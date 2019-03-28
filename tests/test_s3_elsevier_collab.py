# -*- coding: utf-8 -*-
import shutil
from os import path, makedirs

import pytest
from mock import patch

from scrapy.http import TextResponse

from .responses import fake_response_from_file


@pytest.fixture
def results():
    """Return record generator from the Elsevier spider."""
    download_dir = '/tmp/elsevier_test_download_dir/'
    unpack_dir = '/tmp/elsevier_test_unpack_dir/'
    test_file = 'vtex00403986_a-2b_partial_collab.zip'

    with patch('hepcrawl.settings.ELSEVIER_DOWNLOAD_DIR', download_dir),\
         patch('hepcrawl.settings.ELSEVIER_UNPACK_FOLDER', unpack_dir):
            from hepcrawl.spiders import s3_elsevier_spider
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
            records = spider.handle_package(fake_response)

            assert records
            yield records

    shutil.rmtree(download_dir, ignore_errors=True)
    shutil.rmtree(unpack_dir, ignore_errors=True)


def test_authors(results):
    for record in results:
        assert 'authors' in record
        assert len(record['authors']) == 2304


def test_collaborations(results):
    for record in results:
        assert 'collaborations' in record
        assert record['collaborations'] == [{'value': 'The CMS Collaboration'}]


def test_doctype(results):
    for record in results:
        assert 'journal_doctype' in record
        assert record['journal_doctype'] == 'article'
