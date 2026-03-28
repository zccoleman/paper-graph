import os
import requests
import time

def fetch_with_retry(url, max_retries=5, return_full_response=False):
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=30)

            if response.status_code == 200:
                if not return_full_response:
                    return response.json()
                return response

            if response.status_code == 429:
                # Rate limited - wait longer
                wait_time = 2 ** attempt
                time.sleep(wait_time)
                continue

            if response.status_code >= 500:
                # Server error - retry
                wait_time = 2 ** attempt
                time.sleep(wait_time)
                continue

            # Client error - don't retry
            response.raise_for_status()

        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            else:
                raise

    raise Exception(f"Failed after {max_retries} retries")

def lookup_work(id, suppress_errors=False, fields:list[str]=[], api_key=None, ):
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