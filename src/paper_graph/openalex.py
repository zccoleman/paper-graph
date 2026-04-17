from __future__ import annotations

from functools import cached_property
from dataclasses import dataclass, field, fields
import os
import time

from typing import Optional, Literal, Callable, Iterable
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

def paginate_request(request, max_results):
    if not 'per_page' in request:
        request += f'&per_page=100'
    
    cursor = '*'
    results = []
    while cursor is not None and len(results) <= max_results:
        this_request = request + f'&cursor={cursor}'
        this_result = fetch_with_retry(this_request) 
        cursor = this_result['meta']['next_cursor']
        new_results = this_result['results']
        if len(new_results)<=0:
            break
        results.extend(new_results)
    return results

def get_api_key():
    return os.getenv('OPENALEX_KEY')

def count_api_credits(openalex:Optional[OpenAlex]=None):
    """_summary_

    Args:
        openalex (Optional[OpenAlex], optional): _description_. Defaults to None.

    Returns:
        _type_: _description_
    """
    openalex = OpenAlex() if openalex is None else openalex
    def decorator(old_func: Callable):
        def wrapper(*args, **kwargs):
            starting_credits = openalex.credit_check()['credits_used']
            result = old_func(*args, **kwargs)
            ending_credits = openalex.credit_check()['credits_used']
            credits_used = ending_credits - starting_credits
            if result is None:
                return credits_used
            return credits_used, result
        return wrapper
    return decorator


@dataclass
class Work:
    """
    A dataclass containing a subset of the data of a single OpenAlex Work object.

    Attributes:
        id (str): The OpenAlex ID of the work
        doi (str): The Digital Object Identifier of the work
        title (str): The Work's title
        publication_date (str): The publication date in `yyyy-mm-dd` format
        authorships (list[dict]): A highly-nested structure containing authorship metadata
        cited_by_count (int): The number of times the work has been cited
        referenced_works (list[str]): A list of the OpenAlex IDs of the references
        related_works (list[str]): A list of the OpenAlex IDs of related works (as determined by OpenAlex)
    """

    id: str = field(default=None, repr=True)
    doi: str = field(default=None, repr=False)
    title: str = field(default=None, repr=False)
    publication_date: str = field(default=None, repr=False)
    authorships: list[dict] = field(default=None, repr=False)
    cited_by_count: int = field(default=None, repr=False)
    referenced_works: list[str] = field(default=None, repr=False)
    related_works: list[str] = field(default=None, repr=False)


    @classmethod
    def fields(cls):
        return tuple(field.name for field in fields(cls))
    def keys(self):
        return self.fields()
        
    @property
    def is_blank(self) -> bool:
        return self.id is None
    
    def __getitem__(self, key):
        if key not in self.fields():
            raise KeyError(f'Invalid key: {key}. Valid keys are {self.fields()}')
        return getattr(self, key)
    def __setitem__(self, key, value):
        raise TypeError('No')
    
    def __bool__(self):
        return self.id is not None
    
class Works(Sequence[Work]):
    _works: list[Work]
    is_blank: bool

    def __init__(self, works: Iterable[Work], drop_non_existent_works = True):
        self._works = list(works)
        if drop_non_existent_works:
            self._works = list(work for work in self._works if not work.is_blank)

    def __len__(self):
        return len(self._works)
    def __getitem__(self, index):
        return self._works[index]
    def __setitem__(self, key, value):
        raise TypeError('You cannot change an item in a Works sequence')
    
    def append(self, work:Work):
        if not isinstance(work, Work):
            raise TypeError(f'Invalid work: {work}')
        self._works.append(work)
    def __repr__(self):
        ids = ',\n    '.join(f"'{work.id}'" for work in self)
        return f'{self.__class__.__name__}(\n    {ids},\n)'
    
    def to_dataframe(self, process_nested_columns=True):
        
        df = pl.DataFrame(dict(work) for work in self if not work.is_blank)
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

@dataclass(repr=False, frozen=True)
class OpenAlex:
    api_key: str = field(default_factory=get_api_key)

    def credit_check(self):
        result = self._credit_check()
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
    def _credit_check(self):
        request = f"https://api.openalex.org/rate-limit?api_key={self.api_key}"
        result = fetch_with_retry(request)
        return result
    
    def work(self, id, *, raise_if_nonexistent = True) -> Work:
        data = self._work(id, fields=Work.fields(), raise_if_nonexistent=raise_if_nonexistent)
        if not data:
            assert not raise_if_nonexistent
            return Work()
        return Work(**data)
    def _work(self, id: str, fields: Optional[Iterable[str]] = None, *, raise_if_nonexistent = True) -> dict:
        id_candidates = self._get_id_candidates(id)
        for id in id_candidates:
            request = self._work_lookup_html_request(id, fields=fields)
            try: 
                result = fetch_with_retry(request)
                return result
            except HTTPError:
                pass
        if raise_if_nonexistent:
            raise WorkNotFoundError(id)
        return None
    def _get_id_candidates(self, id) -> list[str]:
        candidates = [id]
        if id.startswith('https://openalex.org/W'): ## if we have the full OA URL, shorten to just include the ID to save API credits.
            candidates.insert(0, id.rsplit('/', maxsplit=1)[-1])
        elif id.startswith('10.'): ## if ID looks like a doi but is missing the DOI prefix
            candidates.insert(0, 'doi:' + id)
        elif id.startswith('https://doi.org/10.'):
            candidates.insert(0, 'doi:' + id.lstrip('https://doi.org/'))
        return candidates
    def _work_lookup_html_request(self, id, fields: Optional[list[str]]=None) -> str:
        request = f'https://api.openalex.org/works/{id}?api_key={self.api_key}'
        if fields:
            request += f'&select={','.join(fields)}'
        return request

    def works(self, ids: Iterable[str], *, drop_non_existent_works: bool = True, raise_if_nonexistent: bool = False) -> Works:
        """Returns a Works object from a list of work IDs.

        Args:
            ids (Iterable[str]): A list of work IDs in any form acceptable by the OpenAlex API.
            drop_non_existent_works (bool, optional): Whether to drop works that are not found.
                If False, blank works will remain in the list. Defaults to True.
            raise_if_nonexistent (bool, optional): Whether to raise an error if any work is not found.
                Defaults to False.

        Returns:
            Works
        """
        works = [self.work(id, raise_if_nonexistent=raise_if_nonexistent) for id in ids]
        return Works(works, drop_non_existent_works=drop_non_existent_works)
    
    def works_related_to(
            self,
            work: Work,
            relationship: Literal['similar', 'cited_by', 'citing'],
            sort: Literal['cited_by_count', 'publication_date', 'display_name'] = 'cited_by_count',
            save_api_credits: bool = False,
            max_works: int = 1_000,
        ) -> Works:
        """Returns a Works object containing all of the works related to the input Work by the given relationship.

        Args:
            work (Work): The anchor work to fetch relations from.
            relationship (Literal['similar', 'cited_by', 'citing']): The relation
                to retrieve related works from.
            sort (Literal['cited_by_count', 'publication_date', 'display_name'], Optional): Parameter to sort
                (descending) by. Defaults to 'cited_by_count'.
            save_api_credits (bool): Whether to save API credits by executing
                as a series of singleton searches. Defaults to False.
            max_works (int): The maximum number of works to return. A credit is used for every 100 works.
                Defaults to 1_000.

        Returns:
            Works
        """
        if not isinstance(work, Work):
            raise TypeError(f'work must be a Work, not {type(work)}')
        if save_api_credits:
            return self._works_related_to_save_api_credits(work, relationship, max_works)
            
        id = work.id
        related_works_data: list[dict] = self._works_related_to(id, relationship=relationship, sort=sort, max_works=max_works, fields=Work.fields())
        works = [Work(**data) for data in related_works_data]
        return Works(works, drop_non_existent_works=True)
    def _works_related_to(
            self,
            id: str,
            relationship: Literal['similar', 'cited_by', 'citing'],
            sort: Literal['cited_by_count', 'publication_date', 'display_name'] = 'cited_by_count',
            max_works: int = 1_000,
            fields: Optional[Iterable[str]]=None,
        ) -> list[dict]:
        """Generates and executes an HTTP request to OpenAlex for works related to the 
        given ID, and returns the JSON output.

        Args:
            id (str): The OpenAlex ID of the anchor work
            relationship (Literal['similar', 'cited_by', 'citing']): The relation
                to retrieve related works from.
            max_works (int): The maximum number of works to return
            fields (Optional[Iterable[str]], optional): Fields to select in the request. 
                Will default to the fields listed in the Work dataclass.

        Returns:
            list[dict]: A list of JSONs of the resulting works.
        """
        if not id.startswith('https://openalex.org/W'):
            raise ValueError('Work has invalid OAID:', id)
        id = id.rsplit('/', maxsplit=1)[-1]
        assert id.startswith('W')

        request = self._works_related_to_html_request(id, relationship=relationship, sort=sort, fields=fields)
        try: 
            result = paginate_request(request, max_results=max_works)
            return result
        except HTTPError as e:
            print(request)
            raise e
    def _works_related_to_html_request(
            self,
            id: str,
            relationship: Literal['similar', 'cited_by', 'citing'],
            sort: Optional[Literal['cited_by_count', 'publication_date', 'display_name']] = None,
            fields: Optional[list[str]]=None,
        ) -> str:
        
        relationship_map = {
            'similar': 'related_to',
            'cited_by': 'cited_by',
            'citing': 'referenced_works'
        }
        relationship_name = relationship_map.get(relationship, NotImplemented)
        if relationship_name is NotImplemented:
            raise ValueError(f'Invalid relationship {relationship}')

        request = f'https://api.openalex.org/works?filter={relationship_name}:{id}?api_key={self.api_key}'
        if fields:
            request += f'&select={','.join(fields)}'
        if sort is not None:
            if sort not in ['cited_by_count', 'publication_date', 'display_name']:
                raise ValueError(f'Invalid sort parameter: {sort}')
            request += f'&sort={sort}:desc'
        return request
    def _works_related_to_save_api_credits(self, work: Work, relationship:str, max_works: int):
        relationship_map = {
            'similar': 'related_works',
            'cited_by': 'referenced_works',
            'citing': NotImplemented
        }
        relationship_name = relationship_map.get(relationship, NotImplemented)
        if relationship_name is NotImplemented:
            raise NotImplementedError(f'Cannot do a work-by-work lookup for relationship {relationship}')
        
        related_ids = work[relationship_name][:max_works]
        return self.works(related_ids, drop_non_existent_works=True, raise_if_nonexistent=False)

