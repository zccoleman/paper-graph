import pytest

import os
import requests

from paper_graph.openalex import Work, api_credit_check

def test_api_key():
    key = os.getenv('OPENALEX_KEY')
    assert isinstance(key, str) and len(key)>0, 'Invalid API key set.'

def test_api_credits():
    result = api_credit_check()
    assert result['credits_limit']==10000

def test_work_http_request():
    key = os.getenv('OPENALEX_KEY')
    work_id = 'https://doi.org/10.1088/1361-6455/ac5efa' ## nominal test work
    request = f'https://api.openalex.org/works/{work_id}?api_key={key}'
    result = requests.get(request)
    result = result.json()
    assert result['id'] == 'https://openalex.org/W4220908135' ## known OpenAlex ID of the nominal test work

def test_work_fetch_with_retry():
    from paper_graph.openalex import fetch_with_retry
    api_key = os.getenv('OPENALEX_KEY')
    id = 'doi:10.1088/1361-6455/ac5efa'
    request = f'https://api.openalex.org/works/{id}?api_key={api_key}'
    result = fetch_with_retry(request)
    assert isinstance(result, dict)

def test_manual_work_lookup():
    from paper_graph.openalex import _lookup_work

    work_id = 'https://doi.org/10.1088/1361-6455/ac5efa' ## nominal test work
    result = _lookup_work(work_id)

    assert isinstance(result, dict)
    assert result['id'] == 'https://openalex.org/W4220908135' ## known OpenAlex ID of the nominal test work

def test_requires_id():
    with pytest.raises(TypeError):
        work = Work()

def test_work_class_lookup_oaid():
    '''
    Lookup a work by openalex ID
    '''
    work = Work('https://openalex.org/W4220908135')
    assert 'Exact analytical solution of the driven qutrit in an open quantum system' in work['title']

def test_work_class_lookup_doi():
    '''
    Lookup a work by DOI
    '''
    work = Work('https://doi.org/10.1088/1361-6455/ac5efa')
    assert 'Exact analytical solution of the driven qutrit in an open quantum system' in work['title']

    work = Work('doi:10.1088/1361-6455/ac5efa')
    assert 'Exact analytical solution of the driven qutrit in an open quantum system' in work['title']
