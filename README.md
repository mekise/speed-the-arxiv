<h1>speed-the-arxiv</h1>
<p> It is common practice to read the Arxiv periodically, checking the same sections, the same keywords, and the same authors. Speed-the-arxiv tries to speed these searches up.
    Together with a little HTML, it checks the latest on the Arxiv based on sections, keywords, and authors of choice. 
    These keys are stored in <code>.yaml</code> files and reused every time you run the script. Additional parameters in the file let you personalize the search criteria. 
    In the folder <code>search/</code>, you can have as many <code>.yaml</code> files as you want. You can choose what to search for on the landing page of <code>speedthearxiv.py</code>.
    The script uses Flask to query the Arxiv API and it shows the results in a clean HTML page. It includes collapsible abstracts and links to the articles.
    If needed, it checks and associates the Scirates to each article. Javascript is behind for some dynamicity.
    Ajax takes care of making the search buttons and Flask talk.</p>

<p>⚠️ Fetching the Scirates slows down the app quite a bit. Unfortunately, no API is available for this and I had to fetch it "manually".</p>

<h3>A note on "learned" data</h3>
I thought about using ML (I even started the relative branch) to predict what you might be interested in, but I chose to drop the ball. The reason is simple, I want speed-the-arxiv to return a broader spectrum of results, including some exotic catches. Reading exclusively ad-hoc papers based on your past preferences does not incentivate creativity or change, keys in research. On the other hand, I want you to find something relevant to your work, without losing focus. That is why the search criteria can narrow down the vastest of the fields. There you have it, choose your set of parameters for your search, click the button, and start exploring.

<h3>To-do</h3>
<ul>
    <li><s>Collapsible overview of .yaml parameters to the landing page.</s></li>
    <li><s>Keywords/keyauthors highlighting in HTML, for literal search.</s></li>
    <li><s>Last-modified search file on top of index page.</s></li>
    <li><s>Add folder link to quickly access search files.</s></li>
    <li>Collapsible stats to the search page (keys count etc.).</li>
    <li>Fix occasional events of primary-category/category mishandling (see primary-category and category of example paper https://arxiv.org/abs/2307.06627).</li>
</ul>

<h3>How to use it</h3>
<ul>
    <li>Clone the repo or download</li>
    <li>Change the keys/parameters in the <code>search/config.yaml</code> file. You can create multiple <code>.yaml</code> files to have different searches ready.</li>
    <li>Run <code>python speedthearxiv.py</code> in the terminal.</li>
    <li>Select the search you want from the list.</li>
</ul>
<h3>Dependencies</h3>
<p>You will need some packages. To have everything you need, run in the terminal:</p>
<pre><code">
    pip install flask waitress datetime feedparser requests pyyaml
</code></pre>
<h3>What it looks like</h3>
<img src="https://github.com/mekise/speed-the-arxiv/raw/main/screenshot/speedthearxiv.png?raw=true">
