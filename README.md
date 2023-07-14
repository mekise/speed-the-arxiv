# speed-the-arxiv
It is common practice to read the Arxiv periodically, checking the same sections, the same keywords, and the same authors.
For this reason, I have written this Python script. Together with a little HTML, it checks the latest on the Arxiv based on sections, keywords, and authors of choice.
These keys are stored in the config.yaml file and reused every time you run the script. Additional parameters in the file let you personalize the search criteria.
The script uses Flask to query the Arxiv API and it shows the results in a no-fuss HTML page. It includes collapsible abstracts and links to the articles.
If needed, it checks and associates the Scirates to each article (fetching the scirates slows down the app quite a bit).

### How to use it:
1. Clone the repo or download
2. Change the keys and/or parameters in the search/config.yaml file (**NB:** you can create different versions of the config.yaml file to have ready-to-use search criteria. Just call the right yaml file when you run the script.)
3. Run `python speedthearxiv.py config` in the terminal (if you created another search file called config2.yaml run `python speedthearxiv.py config2` etc.)

### Dependencies:
You will need flask, waitress, datetime, feedparser, requests, pyyaml. To have everything you need, run in the terminal:
```
pip install flask waitress datetime feedparser requests pyyaml
```

### This is what it looks like when you run it:

![speedthearxiv.png](https://github.com/mekise/speed-the-arxiv/raw/main/screenshot/speedthearxiv.png?raw=true)
