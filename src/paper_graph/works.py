import os
import requests

def lookup_work(id, api_key=None, suppress_errors=False, fields:list[str]=[]):
    if not isinstance(id, str):
        raise TypeError('Work ID must be a string.')
    if api_key is None:
        api_key = os.getenv('OPENALEX_KEY')
    
    s = f'https://api.openalex.org/works/{id}?api_key={api_key}'
    if fields:
        s += f'&select={','.join(fields)}'
    try:
        result = requests.get(s)
        result = result.json()
    except Exception as e:
        if suppress_errors:
            return None
        print(id)
        raise e
    return result