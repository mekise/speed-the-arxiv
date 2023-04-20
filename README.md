# speed-the-arxiv
It is common practice to read the Arxiv periodically, checking the same sections, the same keywords, and the same authors. For this reason, I have written this Python script. Together with a little HTML, it checks the latest on the Arxiv based on sections, keywords and authors of choice. These keys are stored as txt file and reused everytime you run the script. It uses Flask to query the Arxiv API and it shows the results in a no-fuss HTML page. It includes collapsible abstracts and links to the articles. In addition, it checks and associate the Scirates to each article (using the Python pkg Scirate).</p>
How to use it:
1. Clone the repo or download
2. Change the keys in keys.txt. Do NOT insert spaces around the commas between entries and do NOT change the template.
3. Run "python speedthearxiv.py" in the terminal

Dependencies:
You will need flask, datetime, feedparser, scirate (with bs4 lxml requests as dependencies). Run a quick "pip install flask datetime feedparser bs4 lxml requests scirate" to have everything you need.

This is what it looks like when you run it:

![speedthearxiv.png](https://github.com/mekise/speed-the-arxiv/raw/main/screenshot/speedthearxiv.png?raw=true)
