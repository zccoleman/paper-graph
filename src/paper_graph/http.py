from dataclasses import dataclass, field
import urllib.parse

@dataclass()
class URLRequest:
    scheme: str
    netloc: str
    path: str
    params: dict
    urlfragment: str
    fragement: str

    def __iter__(self):
        yield from [
            self.scheme,
            self.netloc,
            self.path,
            self.params,
            self.urlfragment,
            self.fragement
        ]
    
    @property
    def url(self) -> str:
        return urllib.parse.urlunparse(self)

@dataclass(init=False)
class OpenAlexWorkRequest(URLRequest):
    scheme: str = field(default='https', init=False)
    netloc: str = field(default='api.openalex.org', init=False)
    path: str = field(default='/works/', init=False)
    urlfragment: str = field(default='', init=False)
    fragement: str = field(default='', init=False)
    params: str

    def __init__(self, work_id='', **kwargs: str):
        self.path = self.path + work_id
        self.params = urllib.parse.urlencode(kwargs)

    