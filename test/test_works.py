import paper_graph

def test_get_work():
    from paper_graph.works import lookup_work

    work_id = 'https://doi.org/10.1038/s42254-019-0054-2' ## nominal test work
    result = lookup_work(work_id)

    assert isinstance(result, dict)
    assert result['id'] == 'https://openalex.org/W2943765333' ## known OpenAlex ID of the nominal test work