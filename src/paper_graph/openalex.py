from functools import cached_property
from dataclasses import dataclass
import os
import time

from typing import Optional, Literal
from collections.abc import Sequence

import requests
import polars as pl

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



def _lookup_work(id, fields:list[str]=[], api_key:Optional[str]=None, ):
    api_key = _check_api_key(api_key)
    if not isinstance(id, str):
        raise TypeError('Work ID must be a string.')
    
    request = f'https://api.openalex.org/works/{id}?api_key={api_key}'
    if fields:
        request += f'&select={','.join(fields)}'
    result = fetch_with_retry(request)
    return result

_fields = [
    'id', 'doi', 'title', 'publication_date', 'authorships', 'cited_by_count', 'referenced_works', 'related_works',
]


@dataclass
class Work:
    id: str
    def __post_init__(self):
        if 'https://openalex.org/W' not in self.id:
            self.id = self['id'] ## getitem will force an item lookup in OA and obtain the OAID.
    
    def __getitem__(self, key):
        if key not in _fields:
            raise ValueError(f'Invalid key: {key}. Valid keys are {_fields}')
        return self.data[key]
    def __setitem__(self, key, value):
        raise TypeError('No')
    
    @cached_property
    def data(self):
        try:
            data = _lookup_work(self.id, fields = _fields)
        except requests.HTTPError:
            del self
            return None
        self.id = data['id']
        return data
        
class Works(Sequence):
    _works: list[Work]

    def __init__(self, *ids):
        self._works = list(Work(id) for id in ids)
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
        ids = ',\n    '.join(work.id for work in self)
        return f'{self.__class__.__name__}(\n    {ids},\n)'
    def _remove_works_without_info(self):
        self._works = [work for work in self if work.data is not None]
    def to_dataframe(self, process_nested_columns=True):
        self._remove_works_without_info()
        df = pl.DataFrame(work.data for work in self)
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

    @classmethod
    def related_to(cls, work:Work):
        raise NotImplementedError

    @classmethod
    def cited_by(cls, work:Work):
        raise NotImplementedError
    
    @classmethod
    def citing(cls, work:Work):
        raise NotImplementedError