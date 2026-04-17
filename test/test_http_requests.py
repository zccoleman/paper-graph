import pytest

import os
import requests

from paper_graph.openalex import fetch_with_retry

def test_api_key():
    key = os.getenv('OPENALEX_KEY')
    assert isinstance(key, str) and len(key)>0, 'Invalid API key set.'

def test_api_credits():
    api_key = os.getenv('OPENALEX_KEY')
    request = f"https://api.openalex.org/rate-limit?api_key={api_key}"
    result = requests.get(request)
    result = result.json()
    assert result['rate_limit']['credits_limit']==10000

def test_work_http_request():
    key = os.getenv('OPENALEX_KEY')
    work_id = 'doi:10.1088/1361-6455/ac5efa' ## nominal test work
    request = f'https://api.openalex.org/works/{work_id}?api_key={key}'
    result = requests.get(request)
    result = result.json()
    assert result['id'] == 'https://openalex.org/W4220908135' ## known OpenAlex ID of the nominal test work

def test_work_fetch_with_retry():
    api_key = os.getenv('OPENALEX_KEY')
    id = 'doi:10.1088/1361-6455/ac5efa' ## nominal test work
    request = f'https://api.openalex.org/works/{id}?api_key={api_key}'
    result = fetch_with_retry(request)

    assert isinstance(result, dict)
    assert result['id'] == 'https://openalex.org/W4220908135' ## known OpenAlex ID of the nominal test work