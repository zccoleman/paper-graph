from functools import cached_property
from dataclasses import dataclass
import os
import time

from typing import Optional, Literal
from collections.abc import Sequence

import requests
from requests import HTTPError
import polars as pl

class WorkNotFoundError(ValueError):
    pass

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

def _check_api_key(api_key):
    if api_key is None:
        api_key = os.getenv('OPENALEX_KEY')
    if not isinstance(api_key, str):
        raise ValueError('Invalid API key type')
    return api_key

def _api_credit_check(api_key:Optional[str]=None):
    api_key = _check_api_key(api_key)
    request = f"https://api.openalex.org/rate-limit?api_key={api_key}"
    result = fetch_with_retry(request)
    return result

def api_credit_check(api_key:Optional[str]=None):
    result = _api_credit_check(api_key)
    rate_limit = result['rate_limit']
    return dict(
        credits_limit = rate_limit['credits_limit'],
        credits_used = rate_limit['credits_used'],
        credits_remaining = rate_limit['credits_remaining'],
        credits_used_fraction = rate_limit['credits_used'] / rate_limit['credits_limit'],
        credits_remaining_fraction = rate_limit['credits_remaining'] / rate_limit['credits_limit'],
        list_queries_remaining = rate_limit['credits_remaining'] // rate_limit['credit_costs']['list'],
        seconds_until_reset = rate_limit['resets_in_seconds'],
        hours_until_reset = rate_limit['resets_in_seconds'] / 3600.,
    )

def count_api_credits(func: callable, api_key:Optional[str]=None):
    def wrapper(*args, **kwargs):
        starting_credits = api_credit_check(api_key=api_key)['credits_used']
        result = func(*args, **kwargs)
        ending_credits = api_credit_check(api_key=api_key)['credits_used']
        # print(f'Credits used: {ending_credits-starting_credits}')
        credits_used = ending_credits - starting_credits
        if result is None:
            return credits_used
        return credits_used, result
    return wrapper

def _lookup_work(id, fields:list[str]=[], api_key:Optional[str]=None, raise_if_nonexistent=True):
    api_key = _check_api_key(api_key)
    if not isinstance(id, str):
        raise TypeError('Work ID must be a string.')
    
    if id.startswith('https://openalex.org/W'): ## if we have the full OA URL, shorten to just include the ID to save API credits.
        old_id = id
        id = id.rsplit('/', maxsplit=1)[-1]
    elif id.startswith('10.'): ## if ID looks like a doi but is missing the DOI prefix
        old_id = id
        id = 'doi:' + id
    elif id.startswith('https://doi.org/'):
        old_id = id
        id = id.lstrip('https://doi.org/')
    else:
        old_id = ''

    
    id_list = [id_candidate for id_candidate in [id, old_id] if id_candidate]
    for id in id_list:
        request = f'https://api.openalex.org/works/{id}?api_key={api_key}'
        if fields:
            request += f'&select={','.join(fields)}'
        try: 
            result = fetch_with_retry(request)
            return result
        except HTTPError:
            pass
    if raise_if_nonexistent:
        raise WorkNotFoundError(id)
    return None
    

_fields = [
    'id',
    'doi',
    'title',
    'publication_date',
    'authorships',
    'cited_by_count',
    'referenced_works',
    'related_works',
]


class Work:
    def __init__(self, id: str, *, lazy_load=False, raise_if_nonexistent=True):
        if not isinstance(id, str):
            raise TypeError(f'Work ID must be a string, not {type(id)}')
        
        self.id = id
        self._raise_if_nonexistent = raise_if_nonexistent
        if not lazy_load:
            self.data

    def __repr__(self):
        return f"{self.__class__.__name__}('{self.id}')"
    def __getitem__(self, key):
        if key not in _fields:
            raise KeyError(f'Invalid key: {key}. Valid keys are {_fields}')
        if self.is_blank:
            raise KeyError('Cannot access data of blank work')
        return self.data[key]
    def __setitem__(self, key, value):
        raise TypeError('No')
    
    @cached_property
    def data(self):
        try:
            data = _lookup_work(self.id, fields = _fields)
        except WorkNotFoundError as e:
            if self._raise_if_nonexistent:
                raise e
            self.is_blank = True
            return {}
        self.is_blank = False
        self.id = data['id']
        return data
    
class Works(Sequence[Work]):
    _works: list[Work]
    is_blank: bool

    def __init__(self, *ids, drop_non_existent_works = True, raise_if_nonexistent=False):
        self._works = list(Work(id, raise_if_nonexistent=raise_if_nonexistent) for id in ids)
        if drop_non_existent_works:
            self._works = list(work for work in self._works if not work.is_blank)

    def __len__(self):
        return len(self._works)
    def __getitem__(self, index):
        return self._works[index]
    def __setitem__(self, key, value):
        raise TypeError('You cannot change an item in a Works sequence')
    def append(self, work:Work|str):
        if isinstance(work, str):
            work = Work(work)
        if not isinstance(work, Work):
            raise TypeError(f'Invalid work: {work}')
        self._works.append(work)
    def __repr__(self):
        ids = ',\n    '.join(f"'{work.id}'" for work in self)
        return f'{self.__class__.__name__}(\n    {ids},\n)'
    
    def to_dataframe(self, process_nested_columns=True):
        
        df = pl.DataFrame(work.data for work in self if not work.is_blank)
        if process_nested_columns:
            df = df.with_columns(
                pl.col('authorships').list.eval(
                    pl.element().struct.field('author').struct.field('display_name')
                ).list.join('; '),
                pl.col('authorships').list.eval(
                    pl.element().struct.field('institutions').explode().struct.field('display_name')
                ).list.unique().list.join('; ').alias('institutions')
            )
        return df
    def to_df(self, *args, **kwargs):
        return self.to_dataframe(*args, **kwargs)

    @classmethod
    def related_to(cls, work:Work|str, save_api_credits = True, raise_if_nonexistent=False):
        if isinstance(work, str):
            work = Work(work)
        
        if not isinstance(work, Work):
            raise TypeError(f'Other work must be a string or a Work, not {type(work)}')
        
        if save_api_credits == True:
            ## Do individual API queries for each ID in the list.
            other_work_ids = work['related_works']
            return cls(*other_work_ids, raise_if_nonexistent=raise_if_nonexistent)
        else:
            ## do an API search for works related to the given ID, and paginate through it. I think this should be faster
            ...

    @classmethod
    def referenced_by(cls, work:Work|str, save_api_credits = True, raise_if_nonexistent=False):
        if isinstance(work, str):
            work = Work(work)
        if save_api_credits == True:
            ## Do individual API queries for each ID in the list. Cheaper but slower.
            other_work_ids = work['referenced_works']
            return cls(*other_work_ids, raise_if_nonexistent=raise_if_nonexistent)
        else:
            ## Do the expensive but probably faster query.
            ...
    
    @classmethod
    def citing(cls, work:Work, save_api_credits = True):
        if save_api_credits == True:
            ## Unfortunately, individual works do not contain the list of works that cite them. We will have to use API credits on this operation
            raise NotImplementedError
        else:
            ...