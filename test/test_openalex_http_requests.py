import pytest

import os
import requests

from paper_graph.openalex import Work, api_credit_check, count_api_credits, _lookup_work, WorkNotFoundError


# @count_api_credits
def test_api_key():
    key = os.getenv('OPENALEX_KEY')
    assert isinstance(key, str) and len(key)>0, 'Invalid API key set.'

# @count_api_credits
def test_api_credits():
    result = api_credit_check()
    assert result['credits_limit']==10000

# @count_api_credits
def test_work_http_request():
    key = os.getenv('OPENALEX_KEY')
    work_id = 'doi:10.1088/1361-6455/ac5efa' ## nominal test work
    request = f'https://api.openalex.org/works/{work_id}?api_key={key}'
    result = requests.get(request)
    result = result.json()
    assert result['id'] == 'https://openalex.org/W4220908135' ## known OpenAlex ID of the nominal test work

# @count_api_credits
def test_work_fetch_with_retry():
    from paper_graph.openalex import fetch_with_retry
    api_key = os.getenv('OPENALEX_KEY')
    id = 'doi:10.1088/1361-6455/ac5efa'
    request = f'https://api.openalex.org/works/{id}?api_key={api_key}'
    result = fetch_with_retry(request)
    assert isinstance(result, dict)

# @count_api_credits
def test_manual_work_lookup():
    work_id = 'doi:10.1088/1361-6455/ac5efa' ## nominal test work
    result = _lookup_work(work_id)

    assert isinstance(result, dict)
    assert result['id'] == 'https://openalex.org/W4220908135' ## known OpenAlex ID of the nominal test work

wrong_doi = '10.1088/1361-6455/ac5efa-WRONG'

def test_doi_prefix_catch():
    work = Work('10.1088/1361-6455/ac5efa')
    assert work['id'] == 'https://openalex.org/W4220908135'

def test_not_found_exception():
    with pytest.raises(WorkNotFoundError):
        _lookup_work(wrong_doi, raise_if_nonexistent=True)

    assert _lookup_work(wrong_doi, raise_if_nonexistent=False) is None

def test_work_with_wrong_id():
    work=Work(wrong_doi, raise_if_nonexistent=False)
    assert work.is_blank
    with pytest.raises(KeyError):
        work['id']

    with pytest.raises(WorkNotFoundError):
        Work(wrong_doi, raise_if_nonexistent=True)
    with pytest.raises(WorkNotFoundError):
        Work(wrong_doi) ## default behavior should be to raise if work is not found
