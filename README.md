# speed-the-arxiv
It is common practice to read the Arxiv periodically, checking the same sections, the same keywords, and the same authors. Speed-the-arxiv tries to speed these searches up. Together with a little HTML, it checks the latest on the Arxiv based on sections, keywords, and authors of choice.
These keys are stored in `.yaml` files and reused every time you run the script. Additional parameters in the file let you personalize the search criteria.
In the folder `search/`, you can have as many `.yaml` files as you want. You can choose what to search for in the landing page of speedthearxiv.py.
The script uses Flask to query the Arxiv API and it shows the results in a clean HTML page. It includes collapsible abstracts and links to the articles.
If needed, it checks and associates the Scirates to each article (fetching the scirates slows down the app quite a bit).
Ajax takes care of making the search buttons and Flask talk.

### How to use it:
1. Clone the repo or download the source.
2. Change the keys and/or parameters in the search/config.yaml file. You can create multiple .yaml files to have different searches ready.
3. Run `python speedthearxiv.py` in the terminal.

### Dependencies:
You will need flask, waitress, datetime, feedparser, requests, pyyaml. To have everything you need, run in the terminal:
```
pip install flask waitress datetime feedparser requests pyyaml
```

### This is what it looks like when you run it:

![speedthearxiv.png](https://github.com/mekise/speed-the-arxiv/raw/main/screenshot/speedthearxiv.png?raw=true)
