import os

import paper_graph

def test_api_key():
    from paper_graph.openalex import fetch_with_retry
    api_key = os.getenv('OPENALEX_KEY')
    id = 'doi:10.1088/1361-6455/ac5efa'
    request = f'https://api.openalex.org/works/{id}?api_key={api_key}'
    result = fetch_with_retry(request)
    assert isinstance(result, dict)


def test_get_work():
    from paper_graph.openalex import lookup_work

    work_id = 'https://doi.org/10.1038/s42254-019-0054-2' ## nominal test work
    result = lookup_work(work_id)

    assert isinstance(result, dict)
    assert result['id'] == 'https://openalex.org/W2943765333' ## known OpenAlex ID of the nominal test work