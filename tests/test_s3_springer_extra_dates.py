

from scrapy.http import TextResponse
from .responses import fake_response_from_file


def test_s3_springer_xml_dates():
    """Test that the correct date is parsed."""
    test_file = 's3_springer_xml/article_with_extra_dates.xml'
    fake_response = fake_response_from_file(
        test_file,
        response_type=TextResponse,
    )

    from hepcrawl.spiders import s3_springer_spider
    spider = s3_springer_spider.S3SpringerSpider()
    records = list(spider.parse(fake_response))

    assert records
    assert len(records) == 1
    assert records[0]['date_published'] == '2019-10-04'
