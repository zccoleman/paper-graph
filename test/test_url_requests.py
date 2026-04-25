import pytest

from paper_graph.http import (
    URLRequest,
    OpenAlexRequest,
    OpenAlexWorkRequest,
)


def test_url_request_format():
    request = URLRequest(
        scheme='scheme',
        netloc='netloc',
        path='path',
        params={'p1': 'v1', 'p2': 'v2'},
        query={'q1': 'a1', 'q2': 'a2'},
        fragment='fragment'
    )
    assert request.url == 'scheme://netloc/path;p1=v1&p2=v2?q1=a1&q2=a2#fragment'

    with pytest.raises(Exception):
        request.fetch()

def test_openalex_request_url():
    
    assert OpenAlexRequest().url == 'https://api.openalex.org/'
    assert OpenAlexRequest('works').url == 'https://api.openalex.org/works'
    assert OpenAlexRequest(query={'p1': 'v1'}).url == 'https://api.openalex.org/?p1=v1'
    assert OpenAlexRequest('works', query={'p1': 'v1'}).url == 'https://api.openalex.org/works?p1=v1'


def test_openalex_work_request():
    assert OpenAlexWorkRequest().url == 'https://api.openalex.org/works/'
    assert OpenAlexWorkRequest(work_id='test_id').url == 'https://api.openalex.org/works/test_id'
    assert OpenAlexWorkRequest('test_id', {'key': 'val'}).url == 'https://api.openalex.org/works/test_id?key=val'
    assert OpenAlexWorkRequest('test_id', key='val').url == 'https://api.openalex.org/works/test_id?key=val'

