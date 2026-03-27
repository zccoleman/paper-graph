import os
import requests

def lookup_work(id, api_key=None):
    if not isinstance(id, str):
        raise TypeError('Work ID must be a string.')
    if api_key is None:
        api_key = os.getenv('OPENALEX_KEY')
    
    s = f'https://api.openalex.org/works/{id}?api_key={api_key}'
    try:
        result = requests.get(s)
        result = result.json()
    except Exception as e:
        raise e
    return result