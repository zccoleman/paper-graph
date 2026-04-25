import pytest

from paper_graph import OpenAlex, Work, Works


fake_OA = OpenAlex('fake_key')

def test_citing_api_request():
    url = fake_OA._works_related_to_html_request(
        id='test_id',
        relationship='citing',
        sort='publication_date',
    )
    assert url == 'https://api.openalex.org/works?filter=referenced_works:test_id?api_key=fake_key&sort=publication_date:desc'

def test_related_api_request():
    url = fake_OA._works_related_to_html_request(
        id='test_id',
        relationship='similar',
        sort='publication_date',
    )
    assert url == 'https://api.openalex.org/works?filter=related_to:test_id?api_key=fake_key&sort=publication_date:desc'

def test_cited_by_api_request():
    url = fake_OA._works_related_to_html_request(
        id='test_id',
        relationship='cited_by',
        sort='publication_date',
    )
    assert url == 'https://api.openalex.org/works?filter=cited_by:test_id?api_key=fake_key&sort=publication_date:desc'



