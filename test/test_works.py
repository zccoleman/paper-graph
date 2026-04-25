import pytest

from paper_graph import OpenAlex, Work, Works


fake_OA = OpenAlex('fake_key')

def test_citing_api_request():
    url = fake_OA._works_related_to_html_request(
        id='test_id',
        relationship='citing',
        sort='publication_date',
    ).url
    assert url == 'https://api.openalex.org/works?filter=referenced_works%3Atest_id&api_key=fake_key&sort=publication_date%3Adesc'

def test_related_api_request():
    url = fake_OA._works_related_to_html_request(
        id='test_id',
        relationship='similar',
        sort='publication_date',
    ).url
    assert url == 'https://api.openalex.org/works?filter=related_to%3Atest_id&api_key=fake_key&sort=publication_date%3Adesc'

def test_cited_by_api_request():
    url = fake_OA._works_related_to_html_request(
        id='test_id',
        relationship='cited_by',
        sort='publication_date',
    ).url
    ## TODO: Parse URLs and verify components are there. Order does not matter
    assert url == 'https://api.openalex.org/works?filter=cited_by%3Atest_id&api_key=fake_key&sort=publication_date%3Adesc'



