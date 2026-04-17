import pytest
import os

from paper_graph.openalex import OpenAlex, Work, count_api_credits, WorkNotFoundError

def test_openalex_init():
    oa = OpenAlex()
    assert oa.api_key == os.getenv('OPENALEX_KEY')

def test_openalex_credit_check():
    oa = OpenAlex()
    assert oa.credit_check()['credits_limit'] == 10_000

def test_credit_counting_without_return():
    oa = OpenAlex()
    @count_api_credits(oa)
    def inner():
        pass
    credits = inner()
    assert credits==0

def test_credit_counting_with_return():
    oa = OpenAlex()
    @count_api_credits(oa)
    def inner():
        return 'yay'
    credits, s = inner()
    assert credits==0
    assert s=='yay'

def test_work_class_lookup_oaid():
    '''
    Lookup a work by openalex ID
    '''
    work = OpenAlex().work('W4220908135')
    assert 'Exact analytical solution of the driven qutrit in an open quantum system' in work['title']

def test_oaid_url_catching():
    oa = OpenAlex()
    @count_api_credits(oa)
    def get_work(id):
        oa.work(id)
    credits = get_work('https://openalex.org/W4220908135')
    assert credits == 0 

def test_doi_vs_oaid():
    '''
    Lookup a work by DOI
    '''
    work = OpenAlex().work('doi:10.1088/1361-6455/ac5efa')
    work2 = OpenAlex().work('W4220908135')
    assert work==work2

def test_doi_catching():
    work = OpenAlex().work('doi:10.1088/1361-6455/ac5efa')
    work2 = OpenAlex().work('10.1088/1361-6455/ac5efa')
    assert work==work2

def test_nonexistent_work_raises():
    OA = OpenAlex()
    with pytest.raises(WorkNotFoundError):
        OA.work('5', raise_if_nonexistent=True)

    with pytest.raises(WorkNotFoundError):
        OA.work('5') ## raise if nonexistent is default

def test_nonexistent_work_behavior():
    OA = OpenAlex()
    blank_work = OA.work('5', raise_if_nonexistent=False)
    assert not blank_work 
    assert blank_work.is_blank
    assert blank_work == Work()
    assert blank_work == Work(None)


    