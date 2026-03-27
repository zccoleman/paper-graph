import os
import requests

def test_api_key():
    key = os.getenv('OPENALEX_KEY')
    assert isinstance(key, str) and len(key)>0

def test_get_work():
    key = os.getenv('OPENALEX_KEY')
    work_id = 'https://doi.org/10.1038/s42254-019-0054-2' ## nominal test work
    request = f'https://api.openalex.org/works/{work_id}?api_key={key}'
    result = requests.get(request)
    result = result.json()

    assert result['id'] == 'https://openalex.org/W2943765333' ## known OpenAlex ID of the nominal test work