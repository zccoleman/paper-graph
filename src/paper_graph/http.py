from dataclasses import dataclass, field
import urllib.parse
import time

import requests

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


@dataclass
class URLRequest:
    """
    Encodes a URL of the form:
    `scheme://netloc/path;param1=val1&param2=val2?query1=filter1&query2=filter2#fragment`
    """
    scheme: str
    netloc: str
    path: str = '/'
    params: dict = field(default_factory=dict)
    query: dict = field(default_factory=dict)
    fragment: str = ''

    def __iter__(self):
        yield from [
            self.scheme,
            self.netloc,
            self.path,
            urllib.parse.urlencode(self.params),
            urllib.parse.urlencode(self.query),
            self.fragment
        ]
    
    @property
    def url(self) -> str:
        return urllib.parse.urlunparse(self)
    
    def fetch(self):
        return fetch_with_retry(self.url)

@dataclass
class OpenAlexRequest(URLRequest):
    scheme: str = field(default='https', init=False)
    netloc: str = field(default='api.openalex.org', init=False)
    ## path
    params: dict[str] = field(default_factory=dict, init=False)
    ## query
    fragment: str = field(default='', init=False)
    

@dataclass
class OpenAlexWorkRequest(OpenAlexRequest):
    def __init__(self, work_id: str = '', query: dict[str] = {}, **kwargs):
        super().__init__(
            path = f'works/{work_id}' if work_id else 'works',
            query = query | kwargs
        )
    