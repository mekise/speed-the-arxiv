# speed-the-arxiv

You know the drill. Wake up, coffee, arXiv. Same sections, same keywords, same authors — every single day. Speed-the-arxiv exists so you can do that in seconds instead of minutes, and maybe enjoy the coffee a bit more.

Define your searches in `.yaml` configs (or create them right from the UI), hit a button, and get a clean page of results with collapsible abstracts, LaTeX rendering, SciRate scores, and one-click BibTeX — no copy-pasting DOIs into twelve different tabs.

Try it with limited functionality: https://mekise.pythonanywhere.com/

## Setup

Clone the repository:

```
git clone https://github.com/mekise/speed-the-arxiv.git
cd speed-the-arxiv
```

Install dependencies using `setup.py`:

```
pip install .
```

Or install them manually:

```
pip install flask requests feedparser pyyaml habanero waitress beautifulsoup4 aiohttp
```

## Usage

1. Edit `search/config.yaml` to set your sections, keywords, and authors. You can also create, edit, duplicate, and delete configs directly from the UI.
2. Run the app:
   ```
   python speedthearxiv.py
   ```
3. A browser window opens at `http://localhost:8080/`. Select a search from the landing page — cache age is displayed next to each search so you know how fresh the results are.
4. Results are loaded via AJAX with an inline spinner on the clicked button. Use the highlight buttons, sort controls, text filter, and pagination to navigate results.

## Search configuration

Each `.yaml` file in `search/` supports the following parameters:

| Parameter | Description |
| --- | --- |
| `max_results` | Maximum number of results to fetch |
| `past_days` | Number of days to look back from today |
| `literal` | Literal (exact phrase) keyword search |
| `run_scirate` | Fetch SciRate scores for each paper |
| `arxiv_sortby` | arXiv sort field (`submittedDate`, `relevance`, `lastUpdatedDate`) |
| `arxiv_sortorder` | arXiv sort order (`descending`, `ascending`) |
| `sortby` | Local sort keys (e.g. `['date', 'scirate']`) |
| `sortorder_rev` | `true` for descending, `false` for ascending |
| `and_or_*` | Logical connectors between keys (`+OR+`, `+AND+`, `+ANDNOT+`) |
| `keys.sections` | arXiv category list (e.g. `[quant-ph, cs.LG]`) |
| `keys.keyauthors` | Author list |
| `keys.keywords` | Keyword list |

See `search/config.yaml` for a complete example.

## Features

- **Configurable searches** — sections, keywords, authors, logical operators, date ranges, all in tidy `.yaml` files you can create, edit, duplicate, and delete from the browser.
- **Dark & light theme** — because not everyone wants to stare into the void (or into the sun).
- **Sort, filter, paginate** — sort by date, SciRate score, or title. Filter results in real time. 25 papers per page so your browser doesn't melt.
- **SciRate scores** — fetched asynchronously with concurrency limits and timeouts, so you get scores without hammering the internet.
- **BibTeX on demand** — auto-generated for every paper, copy to clipboard with one click. Need a specific DOI? The Crossref lookup on the landing page has you covered.
- **Keyword & author highlighting** — toggle-able, so the important bits jump out at you.
- **MathJax** — LaTeX in titles and abstracts rendered properly, as nature intended.
- **Caching** — results are cached locally with a visible age indicator so you know exactly how stale your data is.
- **Robust error handling** — timeouts, API failures, and unreachable endpoints all get friendly messages instead of blank screens.

## Why no ML?

A recommendation engine narrows your reading to papers that look like what you already read. That's great for efficiency, terrible for serendipity. Speed-the-arxiv casts a wider net on purpose — you set the parameters, the search distills the field, and every now and then something unexpected catches your eye. That's the good stuff.

## Screenshot

![speed-the-arxiv](https://github.com/mekise/speed-the-arxiv/raw/main/screenshot/speedthearxiv.png?raw=true)
