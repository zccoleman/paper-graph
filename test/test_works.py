import pytest

from paper_graph.openalex import Work, count_api_credits

def test_requires_id():
    with pytest.raises(TypeError):
        Work()

# @count_api_credits
def test_work_class_lookup_oaid():
    '''
    Lookup a work by openalex ID
    '''
    work = Work('W4220908135')
    assert 'Exact analytical solution of the driven qutrit in an open quantum system' in work['title']

# @count_api_credits
def test_work_class_lookup_doi():
    '''
    Lookup a work by DOI
    '''
    work = Work('doi:10.1088/1361-6455/ac5efa')
    assert 'Exact analytical solution of the driven qutrit in an open quantum system' in work['title']
