import os
import requests
import time

from typing import Optional

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

def check_api_key(api_key):
    if api_key is None:
        api_key = os.getenv('OPENALEX_KEY')
    if not isinstance(api_key, str):
        raise ValueError('Invalid API key type')
    return api_key

def _api_credit_check(api_key:Optional[str]=None):
    api_key = check_api_key(api_key)
    request = f"https://api.openalex.org/rate-limit?api_key={api_key}"
    result = fetch_with_retry(request)
    return result

def api_credit_check(api_key:Optional[str]=None):
    result = _api_credit_check(api_key)
    rate_limit = result['rate_limit']
    return dict(
        fraction_credits_used = rate_limit['credits_used'] / rate_limit['credits_limit'],
        fraction_credits_remaining = rate_limit['credits_remaining'] / rate_limit['credits_limit'],
        list_queries_remaining = rate_limit['credits_remaining'] // rate_limit['credit_costs']['list'],
        seconds_until_reset = rate_limit['resets_in_seconds'],
        hours_until_reset = rate_limit['resets_in_seconds'] / 3600.,
    )


def lookup_work(id, suppress_errors=False, fields:list[str]=[], api_key:Optional[str]=None, ):
    if not isinstance(id, str):
        raise TypeError('Work ID must be a string.')
    api_key = check_api_key(api_key)
    
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