
def test_import():
    import paper_graph

def test_dotenv():
    import os
    # from dotenv import load_dotenv
    # load_dotenv()
    
    test = os.getenv("FAKE_ENV_KEY")
    assert test is None
