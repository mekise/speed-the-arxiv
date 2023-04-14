# speed-the-arxiv
It is common practice to read the Arxiv periodically, checking the same sections, the same keywords, and the same authors. For this reason, I have written this Python script. Together with a little HTML, it checks the latest on the Arxiv based on sections, keywords and authors of choice. It uses Flask to query the Arxiv API and it shows the results in a no-fuss HTML page. It includes collapsible abstracts and links to the articles.</p>
How to use it:
1. Clone the repo or download
2. Change the keys in keys.txt. Do NOT insert spaces around the commas between entries and do NOT change the template.
3. Run speedthearxiv.py

Dependencies:
You will need flask, datetime, feedparser. Run a quick "pip install flask datetime feedparser" to have everything you need.
