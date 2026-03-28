import pytest

from paper_graph.openalex import Work

def test_requires_id():
    with pytest.raises(TypeError):
        work = Work()

def test_work_class_lookup_oaid():
    '''
    Lookup a work by openalex ID
    '''
    work = Work('https://openalex.org/W4220908135')
    assert 'Exact analytical solution of the driven qutrit in an open quantum system' in work['title']

def test_work_class_lookup_doi():
    '''
    Lookup a work by DOI
    '''
    work = Work('https://doi.org/10.1088/1361-6455/ac5efa')
    assert 'Exact analytical solution of the driven qutrit in an open quantum system' in work['title']

    work = Work('doi:10.1088/1361-6455/ac5efa')
    assert 'Exact analytical solution of the driven qutrit in an open quantum system' in work['title']
