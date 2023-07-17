<h1>speed-the-arxiv</h1>
<p> It is common practice to read the Arxiv periodically, checking the same sections, the same keywords, and the same authors. Speed-the-arxiv tries to speed these searches up.
    Together with a little HTML, it checks the latest on the Arxiv based on sections, keywords, and authors of choice. 
    These keys are stored in <code>.yaml</code> files and reused every time you run the script. Additional parameters in the file let you personalize the search criteria. 
    In the folder <code>search/</code>, you can have as many <code>.yaml</code> files as you want. You can choose what to search for on the landing page of <code>speedthearxiv.py</code>.
    The script uses Flask to query the Arxiv API and it shows the results in a clean HTML page. It includes collapsible abstracts and links to the articles.
    If needed, it checks and associates the Scirates to each article (fetching the scirates slows down the app quite a bit).
    Ajax takes care of making the search buttons and Flask talk.</p>

<h3>To-do</h3>
<ul>
    <li>Add keys highlighting in HTML, for literal search.</li>
    <li>Add collapsible stats to the search page (keys count etc.).</li>
</ul>

<h3>How to use it</h3>
<ul>
    <li>Clone the repo or download</li>
    <li>Change the keys/parameters in the <code>search/config.yaml</code> file. You can create multiple <code>.yaml</code> files to have different searches ready.</li>
    <li>Run <code>python speedthearxiv.py</code> in the terminal.</li>
    <li>Select the search you want from the list.</li>
</ul>
<h3>Dependencies</h3>
<p>You will need flask, waitress, datetime, feedparser, requests, pyyaml. To have everything you need, run in the terminal:</p>
<pre><code">
    pip install flask waitress datetime feedparser requests pyyaml
</code></pre>
<h3>What it looks like</h3>
<img src="https://github.com/mekise/speed-the-arxiv/raw/main/screenshot/speedthearxiv.png?raw=true">
