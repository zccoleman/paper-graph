# Paper Graph
This project is an attempt to build a scholarly work exploration tool.

The rough idea of the tool workflow is that it will accept as input the DOI or arXiv ID of a paper then return a list of related papers, ranked or visualized using graph analytics on the citation graph.

The information source is [OpenAlex](https://openalex.org/) ([docs](https://developers.openalex.org/)), which has a robust API, some features of which are accessible for free for a limited number of queries per day. The goal is to streamline the app so that it is feasible to use ~tens of times per day within the limitations of OpenAlex's free mode.

The planned additional dependencies are as follows.
- [Streamlit](https://streamlit.io/) - app interface
- [Altair](https://altair-viz.github.io/) - visualization
- [Polars](https://pola.rs/) - data wrangling
- [iGraph](https://python.igraph.org/en/latest/index.html) - graph analytics
- [leidenalg](https://github.com/vtraag/leidenalg) - graph clustering algorithm

I was also interested in exploring [`rustworkx`](https://www.rustworkx.org/) (a Rust implementation of [`networkx`](https://networkx.org/en/)), but I really like `leidenalg` and it is built on `iGraph`.



## Installation
The source is available at https://github.com/zccoleman/paper-graph.


### Windows
```bash
git clone https://github.com/zccoleman/paper-graph.git
cd paper-graph
python -m venv venv
venv/scripts/activate
pip install -e .[all]
```

### Linux
```bash
git clone https://github.com/zccoleman/paper-graph.git
cd paper-graph
python3 -m venv venv
source venv/bin/activate
pip install -e .[all]
```

### API Key
A `.env` file should be created in the root directory containing your [OpenAlex API key](https://openalex.org/settings/api-key).
```
OPENALEX_KEY = <your_key>
```
