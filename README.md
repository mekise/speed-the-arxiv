# speed-the-arxiv

You know the drill. Wake up, coffee, arXiv. Same sections, same keywords, same authors — every single day. Speed-the-arxiv exists so you can do that in seconds instead of minutes, and maybe enjoy the coffee a bit more.

Define your searches in `.yaml` configs (or create them right from the UI), hit a button, and get a clean page of results with SciRate scores, one-click BibTeX, PDF access, notes, and favourites — no copy-pasting DOIs into twelve different tabs.

## Installation

```bash
pip install speed-the-arxiv
```

## Usage

1. Run the app:
   ```bash
   speedthearxiv
   ```
2. A browser window opens at `http://localhost:8080/`. The home page offers four tools:
   - **speed-the-arxiv** — run your preset `.yaml` searches against the arXiv API.
   - **search-the-arxiv** — direct free-text search of the arXiv API.
   - **layer-the-arxiv** — browse arxiv.org directly with your speed-the-arxiv tools (favourites, notes, BibTeX) overlaid on top.
   - **search-the-crossref** — look up any DOI and get a formatted BibTeX entry instantly.

3. Edit or create search configs from the UI, or drop `.yaml` files in the `search/` directory. Cache age is displayed next to each search so you know how fresh the results are.

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

- **Preset searches** — define sections, keywords, authors, logical operators, and date ranges in tidy `.yaml` files you can create, edit, duplicate, and delete from the browser.
- **arXiv layer** — browse arxiv.org natively with your tools (favourites, notes, BibTeX) injected into every paper listing.
- **SciRate scores** — fetched asynchronously so you see community interest at a glance without hammering the API.
- **BibTeX on demand** — auto-generated for every paper, copy to clipboard with one click. Crossref DOI lookup also available from the home page.
- **Favourites & notes** — star papers and attach personal notes, persisted across sessions.
- **Keyword & author highlighting** — toggle-able, so the important bits jump out at you.
- **Sort, filter, paginate** — sort by date, SciRate score, or title; filter results in real time.
- **MathJax** — LaTeX in titles and abstracts rendered properly, as nature intended.
- **Dark & light theme** — because not everyone wants to stare into the void (or into the sun).
- **Caching** — results are cached locally with a visible age indicator so you know exactly how stale your data is.

## Screenshots

![Home](https://github.com/mekise/speed-the-arxiv/raw/main/screenshot/speedthearxiv_home.png)

![Results](https://github.com/mekise/speed-the-arxiv/raw/main/screenshot/speedthearxiv_results.png)
