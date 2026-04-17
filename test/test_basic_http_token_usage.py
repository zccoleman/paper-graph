import pytest

import os
import requests

from paper_graph.openalex import count_api_credits

   
def test_raw_request():
    @count_api_credits()
    def test_work_http_request():
        key = os.getenv('OPENALEX_KEY')
        work_id = 'doi:10.1088/1361-6455/ac5efa' ## nominal test work
        request = f'https://api.openalex.org/works/{work_id}?api_key={key}'
        result = requests.get(request)
        result = result.json()
        assert result['id'] == 'https://openalex.org/W4220908135' ## known OpenAlex ID of the nominal test work
    assert test_work_http_request()==0

def test_fetch_with_retry():
    @count_api_credits()
    def test_work_fetch_with_retry():
        from paper_graph.openalex import fetch_with_retry
        api_key = os.getenv('OPENALEX_KEY')
        id = 'doi:10.1088/1361-6455/ac5efa'
        request = f'https://api.openalex.org/works/{id}?api_key={api_key}'
        result = fetch_with_retry(request)
        assert isinstance(result, dict)
    assert test_work_fetch_with_retry()==0


