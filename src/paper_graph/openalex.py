from __future__ import annotations

from functools import cached_property
from dataclasses import dataclass, field, fields
import os
import time

from typing import Optional, Literal, Callable, Iterable, overload, Self
from collections.abc import Sequence

import requests
from requests import HTTPError
import polars as pl

from paper_graph.http import fetch_with_retry, URLRequest, OpenAlexRequest, OpenAlexWorkRequest

class WorkNotFoundError(ValueError):
    pass



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
    
    @overload
    def __getitem__(self, index: int) -> Work: ...
    @overload
    def __getitem__(self, s: slice) -> Self: ...
    def __getitem__(self, key: slice|int):
        return self._works[key]
    
    def __setitem__(self, key, value):
        raise TypeError('You cannot change an item in a Works sequence')
    
    @property
    def ids(self):
        return [work.id for work in self]
    
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
        request = OpenAlexRequest(path='rate-limit', query={'api_key': self.api_key})
        result = request.fetch()
        return result
    
    def work(
            self,
            id: str,
            *,
            raise_if_nonexistent: bool = True,
            ) -> Work:
        """
        Retrievves a specific work from OpenAlex from an ID.

        Args:
            id (str): The ID of the work. Primarily designed for an OpenAlex 
                ID or a DOI, but may work for other IDs that OA recognizes.
            raise_if_nonexistent (bool, optional): Whether to raise an error 
                if the work cannot be found in OpenAlex. If False, a blank
                Work object will be returned in this case. Defaults to True.

        Returns:
            Work
        """
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
                result = request.fetch()
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
    def _work_lookup_html_request(self, id, fields: Optional[list[str]]=None) -> URLRequest:
        query = {
            'api_key': self.api_key
        }
        if fields:
            query['select'] = ','.join(fields)

        request = OpenAlexWorkRequest(work_id=id, query=query)
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
        ) -> URLRequest:
        
        relationship_map = {
            'similar': 'related_to',
            'cited_by': 'cited_by',
            'citing': 'referenced_works'
        }
        relationship_name = relationship_map.get(relationship, NotImplemented)
        if relationship_name is NotImplemented:
            raise ValueError(f'Invalid relationship {relationship}')

        query = {
            'filter': f'{relationship_name}:{id}',
            'api_key': self.api_key
        }
        if fields:
            query['select'] = ','.join(fields)

        if sort is not None:
            if sort not in ['cited_by_count', 'publication_date', 'display_name']:
                raise ValueError(f'Invalid sort parameter: {sort}')
            query['sort'] = f'{sort}:desc'

        request = OpenAlexWorkRequest(work_id='', query=query)
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

