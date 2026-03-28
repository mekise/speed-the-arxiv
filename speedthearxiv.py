import os
import json
import platform
import subprocess
import yaml
import requests

ARXIV_HEADERS = {'User-Agent': 'speed-the-arxiv/1.0 (https://github.com/mekise/speed-the-arxiv)'}
import feedparser
import asyncio
import aiohttp
import webbrowser
import datetime as dt
from flask import Flask, render_template, request, jsonify
from habanero import cn
from bs4 import BeautifulSoup

app_port = 8080
app = Flask(__name__)
CACHE_DIR = './cache'
os.makedirs(CACHE_DIR, exist_ok=True)
FAVOURITES_FILE = './favourites.json'
NOTES_DIR = './notes'
os.makedirs(NOTES_DIR, exist_ok=True)

def load_favourites():
    if os.path.exists(FAVOURITES_FILE):
        try:
            with open(FAVOURITES_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []
    return []

def save_favourites(favs):
    with open(FAVOURITES_FILE, 'w') as f:
        json.dump(favs, f, indent=2)

@app.route("/")
def index():
    return _render_index()

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/favourites", methods=['GET'])
def favourites():
    papers = load_favourites()
    return render_template("favourites.html", papers=papers)

@app.route("/toggle_favourite", methods=['POST'])
def toggle_favourite():
    data = request.get_json()
    arxiv_id = str(data.get('arxiv_id', '')).strip()
    if not arxiv_id:
        return jsonify({"error": "Missing arxiv_id"}), 400
    favs = load_favourites()
    existing = next((f for f in favs if f['arxiv_id'] == arxiv_id), None)
    if existing:
        favs = [f for f in favs if f['arxiv_id'] != arxiv_id]
        is_fav = False
    else:
        favs.append({
            'arxiv_id': arxiv_id,
            'title': data.get('title', ''),
            'authors': data.get('authors', ''),
            'date': data.get('date', ''),
            'abs_url': data.get('abs_url', ''),
            'pdf_url': data.get('pdf_url', ''),
            'bibtex': data.get('bibtex', ''),
            'category': data.get('category', ''),
            'summary': data.get('summary', ''),
            'added_at': dt.datetime.now().strftime('%Y-%m-%d'),
        })
        is_fav = True
    save_favourites(favs)
    return jsonify({"is_fav": is_fav})

@app.route("/get_note/<arxiv_id>", methods=['GET'])
def get_note(arxiv_id):
    if '/' in arxiv_id or '\\' in arxiv_id or '..' in arxiv_id:
        return jsonify({"error": "Invalid arxiv_id"}), 400
    note_path = os.path.join(NOTES_DIR, arxiv_id + '.md')
    content = ''
    if os.path.exists(note_path):
        with open(note_path, 'r') as f:
            content = f.read()
    return jsonify({"content": content})

@app.route("/has_note/<arxiv_id>", methods=['GET'])
def has_note(arxiv_id):
    if '/' in arxiv_id or '\\' in arxiv_id or '..' in arxiv_id:
        return jsonify({"error": "Invalid arxiv_id"}), 400
    note_path = os.path.join(NOTES_DIR, arxiv_id + '.md')
    return jsonify({"has_note": os.path.exists(note_path)})

@app.route("/delete_note/<arxiv_id>", methods=['POST'])
def delete_note(arxiv_id):
    if '/' in arxiv_id or '\\' in arxiv_id or '..' in arxiv_id:
        return jsonify({"error": "Invalid arxiv_id"}), 400
    note_path = os.path.join(NOTES_DIR, arxiv_id + '.md')
    if os.path.exists(note_path):
        os.remove(note_path)
    return jsonify({"deleted": True})

@app.route("/save_note", methods=['POST'])
def save_note():
    data = request.get_json()
    arxiv_id = str(data.get('arxiv_id', '')).strip()
    if not arxiv_id or '/' in arxiv_id or '\\' in arxiv_id or '..' in arxiv_id:
        return jsonify({"error": "Invalid arxiv_id"}), 400
    note_path = os.path.join(NOTES_DIR, arxiv_id + '.md')
    with open(note_path, 'w') as f:
        f.write(data.get('content', ''))
    favs = load_favourites()
    auto_starred = False
    if not any(f['arxiv_id'] == arxiv_id for f in favs):
        favs.append({
            'arxiv_id': arxiv_id,
            'title': data.get('title', ''),
            'authors': data.get('authors', ''),
            'date': data.get('date', ''),
            'abs_url': data.get('abs_url', ''),
            'pdf_url': data.get('pdf_url', ''),
            'bibtex': data.get('bibtex', ''),
            'category': data.get('category', ''),
            'summary': data.get('summary', ''),
            'added_at': dt.datetime.now().strftime('%Y-%m-%d'),
        })
        save_favourites(favs)
        auto_starred = True
    return jsonify({"saved": True, "auto_starred": auto_starred})

@app.route("/doi", methods=['POST'])
def doi():
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        data = request.get_json()
        search_query = data.get('doi', '').strip()
    else:
        search_query = request.form.get('search_query', '').strip()
    # Strip common URL prefixes to extract bare DOI
    for prefix in ['https://doi.org/', 'http://doi.org/', 'https://dx.doi.org/', 'http://dx.doi.org/']:
        if search_query.lower().startswith(prefix):
            search_query = search_query[len(prefix):]
            break
    if not search_query:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({"error": "Please enter a DOI"}), 400
        return _render_index(error="Please enter a DOI")
    try:
        bibtex = cn.content_negotiation(ids=search_query, format="bibentry")
        bibtex = format_bibtex_string(bibtex)
    except Exception as e:
        error_msg = f"Could not resolve DOI: {search_query}"
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({"error": error_msg}), 404
        return _render_index(error=error_msg)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({"bibtex": bibtex})
    return _render_index(bibtex=bibtex)

def _render_index(**kwargs):
    searches = [os.path.splitext(file)[0] for file in os.listdir('./search') if file.endswith('.yaml')]
    searches.sort(key=lambda x: os.path.getmtime('./search/'+x+'.yaml'), reverse=True)
    search_list = [read_config(s) for s in searches]
    for item in search_list:
        cached = load_cache(item['name'])
        if cached and cached.get('fetched_at'):
            try:
                fetched = dt.datetime.strptime(cached['fetched_at'], '%Y-%m-%d %H:%M:%S')
                delta = dt.datetime.now() - fetched
                total_min = int(delta.total_seconds() // 60)
                if total_min < 60:
                    item['cache_age'] = f"{total_min}m ago"
                elif total_min < 1440:
                    item['cache_age'] = f"{total_min // 60}h ago"
                else:
                    item['cache_age'] = f"{total_min // 1440}d ago"
            except (ValueError, TypeError):
                item['cache_age'] = None
        else:
            item['cache_age'] = None
    return render_template('index.html', search_list=search_list, **kwargs)

@app.route("/search", methods=['POST'])
def search():
    if request.method == "POST":
        data = request.get_json()
    config = read_config(data['search'])
    cached = load_cache(config['name'])
    if cached:
        config_changed = cached.get('config') is not None and cached['config'] != _search_params(config)
        return render_search(config, cached['papers'], cached['fetched_at'], config_changed=config_changed)
    return do_fetch_and_render(config)

@app.route("/arxiv_search", methods=['POST'])
def arxiv_search():
    data = request.get_json()
    query_text = data.get('query', '').strip()
    field = data.get('field', 'all')
    max_results = int(data.get('max_results', 50))
    sortby = data.get('sortby', 'relevance')
    sortorder = data.get('sortorder', 'descending')

    if not query_text:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({"error": "Please enter a search query"}), 400
        return _render_index(error="Please enter a search query")

    # Build arxiv API search query
    allowed_fields = {'all', 'ti', 'au', 'abs', 'cat', 'co', 'jr', 'id'}
    if field not in allowed_fields:
        field = 'all'
    if max_results < 1:
        max_results = 1
    elif max_results > 500:
        max_results = 500

    # URL-encode the query
    if field == 'id':
        url = f"https://export.arxiv.org/api/query?id_list={query_text.replace(' ', ',')}&start=0&max_results={max_results}"
    else:
        encoded_query = f"{field}:{query_text}".replace(" ", "%20")
        url = f"https://export.arxiv.org/api/query?search_query={encoded_query}&start=0&max_results={max_results}&sortBy={sortby}&sortOrder={sortorder}"

    try:
        response = requests.get(url, headers=ARXIV_HEADERS, timeout=120)
    except requests.exceptions.Timeout:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({"error": "arXiv API timed out. Try again later."}), 504
        return _render_index(error="arXiv API timed out.")
    except requests.exceptions.RequestException:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({"error": "Could not reach arXiv API."}), 502
        return _render_index(error="Could not reach arXiv API.")

    if response.status_code == 429:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({"error": "arXiv API rate limit reached. Please wait a moment and try again."}), 429
        return _render_index(error="arXiv API rate limit reached. Please wait a moment and try again.")

    if response.status_code == 200:
        feeds = feedparser.parse(response.text)
        if feeds.entries and feeds.entries[0].id.startswith('https://arxiv.org/api/errors'):
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({"error": "arXiv API returned an error. Try simplifying your query."}), 502
            return _render_index(error="arXiv API returned an error.")

        papers = []
        for entry in feeds.entries:
            paper = process_entry_adhoc(entry)
            if paper:
                papers.append(paper)

        fetched_at = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        adhoc_params = {
            'query': query_text,
            'field': field,
            'max_results': max_results,
            'sortby': sortby,
            'sortorder': sortorder,
        }

        fav_ids = {f['arxiv_id'] for f in load_favourites()}
        template_args = dict(
            papers=papers,
            keyauthors=[],
            keywords=[query_text] if field != 'au' else [],
            sections=[],
            search_name=f"search: {field}:{query_text}",
            run_scirate=False,
            fetched_at=fetched_at,
            cache_stale=False,
            config_changed=False,
            adhoc_search=adhoc_params,
            favourite_ids=fav_ids,
        )
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return render_template("search_content.html", **template_args)
        return render_template("search.html", **template_args)
    else:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({"error": f"arXiv API returned status {response.status_code}."}), 502
        return _render_index(error=f"arXiv API returned status {response.status_code}.")

@app.route("/save_adhoc_search", methods=['POST'])
def save_adhoc_search():
    data = request.get_json()
    name = data.get('name', '').strip()
    if not name or '/' in name or '\\' in name or '..' in name:
        return jsonify({"error": "Invalid search name"}), 400
    config_path = os.path.join('search', name + '.yaml')
    if os.path.exists(config_path):
        return jsonify({"error": "A search with this name already exists"}), 409

    query = data.get('query', '').strip()
    field = data.get('field', 'all')
    max_results = int(data.get('max_results', 50))
    sortby = data.get('sortby', 'relevance')
    sortorder = data.get('sortorder', 'descending')

    # Map ad-hoc search to Speed the Arxiv config format
    sections = []
    keyauthors = []
    keywords = []

    terms = [t.strip() for t in query.split(',') if t.strip()] if ',' in query else [query]

    if field == 'cat':
        sections = terms
    elif field == 'au':
        keyauthors = terms
    else:
        keywords = terms

    config = {
        'max_results': max_results,
        'past_days': 365,
        'literal': field not in ('au', 'cat'),
        'run_scirate': False,
        'arxiv_sortby': sortby,
        'arxiv_sortorder': sortorder,
        'sortby': ['date'],
        'sortorder_rev': True,
        'and_or_sections': '+OR+',
        'and_or_keyauthors': '+OR+',
        'and_or': '+OR+',
        'and_or_keywords': '+OR+',
        'keys': {
            'sections': sections,
            'keyauthors': keyauthors,
            'keywords': keywords,
        }
    }
    with open(config_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=None, sort_keys=False)
    return jsonify({"message": "Search saved", "name": name})

@app.route("/refresh", methods=['POST'])
def refresh():
    if request.method == "POST":
        data = request.get_json()
    config = read_config(data['search'])
    return do_fetch_and_render(config)

def do_fetch_and_render(config):
    query_sections = [f"cat:{section}" for section in config['sections']]
    query_keyauthors = [f"au:{keyauthor}" for keyauthor in config['keyauthors']]
    if config['literal']:
        query_keywords = [f"all:\"{keyword}\"" for keyword in config['keywords']]
    else:
        query_keywords = [f"all:{keyword}" for keyword in config['keywords']]
    if len(config['sections']) and len(config['keyauthors']) and len(config['keywords']):
        query = config['and_or_sections'].join(query_sections) + "+AND+%28" + config['and_or_keyauthors'].join(query_keyauthors) + config['and_or'] + config['and_or_keywords'].join(query_keywords) + "%29"
    elif len(config['sections']) and len(config['keyauthors']):
        query = config['and_or_sections'].join(query_sections) + "+AND+%28" + config['and_or_keyauthors'].join(query_keyauthors) + "%29"
    elif len(config['sections']) and len(config['keywords']):
        query = config['and_or_sections'].join(query_sections) + "+AND+%28" + config['and_or_keywords'].join(query_keywords) + "%29"
    elif len(config['keyauthors']) and len(config['keywords']):
        query = config['and_or_keyauthors'].join(query_keyauthors) + config['and_or'] + config['and_or_keywords'].join(query_keywords)
    elif len(config['sections']):
        query = config['and_or_sections'].join(query_sections)
    elif len(config['keyauthors']):
        query = config['and_or_keyauthors'].join(query_keyauthors)
    elif len(config['keywords']):
        query = config['and_or_keywords'].join(query_keywords)    
    query = query.replace(" ", "%20")
    url = f"https://export.arxiv.org/api/query?search_query={query}&start=0&max_results={config['max_results']}&sortBy={config['arxiv_sortby']}&sortOrder={config['arxiv_sortorder']}"
    try:
        response = requests.get(url, headers=ARXIV_HEADERS, timeout=120)
    except requests.exceptions.Timeout:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({"error": "arXiv API timed out. Try again later."}), 504
        return render_search(config, [], None)
    except requests.exceptions.RequestException:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({"error": "Could not reach arXiv API."}), 502
        return render_search(config, [], None)
    if response.status_code == 429:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({"error": "arXiv API rate limit reached. Please wait a moment and try again."}), 429
        return render_search(config, [], None)
    if response.status_code == 200:
        feeds = feedparser.parse(response.text)
        # Detect arXiv API error entries
        if feeds.entries and feeds.entries[0].id.startswith('https://arxiv.org/api/errors'):
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({"error": "arXiv API returned an error. The query may be too complex. Try reducing max_results."}), 502
            return render_search(config, [], None)
        arxiv_ids = [entry.id.split('/')[-1] for entry in feeds.entries]
        # First pass: filter by date, collect entries that survive
        filtered = []
        for i, entry in enumerate(feeds.entries):
            paper = process_entry(entry, config['past_days'], 0)
            if paper:
                filtered.append((i, paper))
        # Fetch scirates only for surviving papers
        if config['run_scirate'] and filtered:
            surviving_ids = [arxiv_ids[i] for i, _ in filtered]
            scirates = asyncio.run(get_scirates_async(surviving_ids))
            for idx, (_, paper) in enumerate(filtered):
                paper['scirate'] = scirates[idx]
        papers = [paper for _, paper in filtered]
        papers.sort(key=lambda x:tuple([x[ele] for ele in config['sortby']]), reverse=config['sortorder_rev'])
        fetched_at = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        save_cache(config['name'], papers, fetched_at, config)
        return render_search(config, papers, fetched_at)
    else:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({"error": f"arXiv API returned status {response.status_code}. Try again later or reduce query complexity."}), 502
        return render_search(config, [], None)

def render_search(config, papers, fetched_at, config_changed=False):
    cache_stale = False
    if fetched_at:
        try:
            fetched = dt.datetime.strptime(fetched_at, '%Y-%m-%d %H:%M:%S')
            cache_stale = (dt.datetime.now() - fetched).total_seconds() > 86400
        except (ValueError, TypeError):
            pass
    fav_ids = {f['arxiv_id'] for f in load_favourites()}
    template_args = dict(papers=papers,
        keyauthors=[keyauthor for keyauthor in config["keyauthors"]],
        keywords=[keyword for keyword in config["keywords"]],
        sections=[section for section in config["sections"]],
        search_name=config['name'], run_scirate=config['run_scirate'],
        fetched_at=fetched_at, cache_stale=cache_stale,
        config_changed=config_changed, adhoc_search=None,
        favourite_ids=fav_ids)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template("search_content.html", **template_args)
    return render_template("search.html", **template_args)

def load_cache(search_name):
    cache_path = os.path.join(CACHE_DIR, search_name + '.json')
    if os.path.exists(cache_path):
        with open(cache_path, 'r') as f:
            return json.load(f)
    return None

_SEARCH_CONFIG_KEYS = [
    'sections', 'keywords', 'keyauthors',
    'and_or_sections', 'and_or_keyauthors', 'and_or', 'and_or_keywords',
    'max_results', 'past_days', 'literal', 'run_scirate',
    'arxiv_sortby', 'arxiv_sortorder',
]

def _search_params(config):
    return {k: config[k] for k in _SEARCH_CONFIG_KEYS}

def save_cache(search_name, papers, fetched_at, config):
    cache_path = os.path.join(CACHE_DIR, search_name + '.json')
    with open(cache_path, 'w') as f:
        json.dump({'papers': papers, 'fetched_at': fetched_at,
                   'config': _search_params(config)}, f)

def read_config(name):
    with open('search/'+str(name)+'.yaml', 'r') as file:
        config = yaml.safe_load(file)
    return {
        "name": name,
        "max_results": config['max_results'],
        "past_days": config['past_days'],
        "literal": config['literal'],
        "run_scirate": config['run_scirate'],
        "arxiv_sortby": config['arxiv_sortby'],
        "arxiv_sortorder": config['arxiv_sortorder'],
        "sortby": config['sortby'],
        "sortorder_rev": config['sortorder_rev'],
        "and_or_sections": config['and_or_sections'],
        "and_or_keyauthors": config['and_or_keyauthors'],
        "and_or": config['and_or'],
        "and_or_keywords": config['and_or_keywords'],
        "sections": config['keys']['sections'],
        "keyauthors": config['keys']['keyauthors'],
        "keywords": config['keys']['keywords']
    }

SCIRATE_SEMAPHORE_LIMIT = 20
SCIRATE_TIMEOUT = 10

async def fetch_scirate(session, arxiv_id, semaphore):
    url = f"https://scirate.com/arxiv/{arxiv_id}"
    async with semaphore:
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=SCIRATE_TIMEOUT)) as response:
                html = await response.text()
                soup = BeautifulSoup(html, "html.parser")
                btn = soup.find("button", {"class": "btn btn-default count"})
                return int(btn.text.strip()) if btn else 0
        except Exception:
            return -1
    
async def get_scirates_async(arxiv_ids):
    semaphore = asyncio.Semaphore(SCIRATE_SEMAPHORE_LIMIT)
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_scirate(session, arxiv_id, semaphore) for arxiv_id in arxiv_ids]
        return await asyncio.gather(*tasks)
    
def process_entry(entry, past_days, scirate):
    checkdate = entry.updated[0:10]
    entry_date = dt.date.fromisoformat(checkdate)
    if dt.date.today() - entry_date <= dt.timedelta(days=past_days):
        return _build_paper_dict(entry, checkdate, scirate)
    return None

def process_entry_adhoc(entry):
    """Process an arxiv entry without date filtering (for ad-hoc searches)."""
    checkdate = entry.updated[0:10]
    return _build_paper_dict(entry, checkdate, 0)

def _build_paper_dict(entry, checkdate, scirate):
    primary_cat = entry.get('arxiv_primary_category', {}).get('term', '')
    all_cats = [tag['term'] for tag in entry.get('tags', [])]
    other_cats = [cat for cat in all_cats if cat != primary_cat]
    if other_cats:
        category = primary_cat + " (" + ", ".join(other_cats) + ")"
    else:
        category = primary_cat
    arxiv_id = entry.id.split('/abs/')[-1]
    arxiv_id_clean = arxiv_id.split('v')[0]
    first_author = entry.authors[0].name.split()[-1].lower() if entry.authors else 'unknown'
    year = checkdate[:4]
    authors_bibtex = " and ".join(author.name for author in entry.authors)
    related_doi = entry.get('arxiv_doi', '')
    doi = related_doi or f"10.48550/arXiv.{arxiv_id_clean}"
    doi_line = f"\tdoi={{{doi}}},\n" if doi else ""
    bibtex = (f"@article{{{first_author}{year}{arxiv_id_clean},\n"
              f"\ttitle={{{entry.title}}},\n"
              f"\tauthor={{{authors_bibtex}}},\n"
              f"\tyear={{{year}}},\n"
              f"{doi_line}"
              f"\teprint={{{arxiv_id_clean}}},\n"
              f"\tarchivePrefix={{arXiv}},\n"
              f"\tprimaryClass={{{primary_cat}}}\n}}")
    return {
        "arxiv_id": arxiv_id_clean,
        "title": entry.title,
        "authors": ", ".join(author.name for author in entry.authors),
        "summary": entry.summary,
        "date": checkdate,
        "category": category,
        "abs_url": entry.link,
        "pdf_url": entry.link.replace('/abs/', '/pdf/'),
        "scirate": scirate,
        "bibtex": bibtex,
        "related_doi": related_doi
    }
    
def format_bibtex_string(input_string):
    formatted_string = input_string.replace(' @', '@').replace(', title={', ',\n\ttitle={').replace('}, ', '},\n\t').replace('} }', '}\n}')
    idx = formatted_string.find('month=')
    if idx != -1 and formatted_string[idx+9]==',':
        formatted_string = formatted_string[:idx+10] + '\n\t' + formatted_string[idx+11:]
    elif idx != -1:
        formatted_string = formatted_string[:idx+10] + '\n' + formatted_string[idx+10:]
    return formatted_string

@app.route('/open_folder', methods=['POST'])
def open_folder():
    try:
        folder_path = './search'
        command = None
        if platform.system() == 'Linux':
            command = ['xdg-open', folder_path]
        elif platform.system() == 'Darwin':
            command = ['open', folder_path]
        elif platform.system() == 'Windows':
            command = ['explorer', folder_path]
        if command:
            subprocess.Popen(command)
            return jsonify({"message": "Folder opened successfully!"})
        else:
            return jsonify({"error": "Unsupported operating system"})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/save_config', methods=['POST'])
def save_config():
    data = request.get_json()
    name = data.get('name', '').strip()
    if not name or '/' in name or '\\' in name or '..' in name:
        return jsonify({"error": "Invalid config name"}), 400
    config_path = os.path.join('search', name + '.yaml')
    if not os.path.exists(config_path):
        return jsonify({"error": "Config not found"}), 404
    config = _build_config_dict(data)
    with open(config_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=None, sort_keys=False)
    return jsonify({"message": "Config saved"})

@app.route('/new_config', methods=['POST'])
def new_config():
    data = request.get_json()
    name = data.get('name', '').strip()
    if not name or '/' in name or '\\' in name or '..' in name:
        return jsonify({"error": "Invalid config name"}), 400
    config_path = os.path.join('search', name + '.yaml')
    if os.path.exists(config_path):
        return jsonify({"error": "Config already exists"}), 409
    config = _build_config_dict(data)
    with open(config_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=None, sort_keys=False)
    return jsonify({"message": "Config created"})

@app.route('/delete_config', methods=['POST'])
def delete_config():
    data = request.get_json()
    name = data.get('name', '').strip()
    if not name or '/' in name or '\\' in name or '..' in name:
        return jsonify({"error": "Invalid config name"}), 400
    config_path = os.path.join('search', name + '.yaml')
    if not os.path.exists(config_path):
        return jsonify({"error": "Config not found"}), 404
    os.remove(config_path)
    cache_path = os.path.join(CACHE_DIR, name + '.json')
    if os.path.exists(cache_path):
        os.remove(cache_path)
    return jsonify({"message": "Config deleted"})

@app.route('/get_config', methods=['POST'])
def get_config():
    data = request.get_json()
    name = data.get('name', '').strip()
    if not name or '/' in name or '\\' in name or '..' in name:
        return jsonify({"error": "Invalid config name"}), 400
    config_path = os.path.join('search', name + '.yaml')
    if not os.path.exists(config_path):
        return jsonify({"error": "Config not found"}), 404
    config = read_config(name)
    # Convert booleans to lowercase strings and format select values for the frontend
    result = {}
    for key, val in config.items():
        if isinstance(val, bool):
            result[key] = 'true' if val else 'false'
        elif isinstance(val, list):
            result[key] = val
        else:
            result[key] = val
    return jsonify(result)

def _build_config_dict(data):
    sections = [s.strip() for s in data.get('sections', '').split(',') if s.strip()]
    keyauthors = [s.strip() for s in data.get('keyauthors', '').split(',') if s.strip()]
    keywords = [s.strip() for s in data.get('keywords', '').split(',') if s.strip()]
    sortby = [s.strip() for s in data.get('sortby', 'date').split(',') if s.strip()]
    return {
        'max_results': int(data.get('max_results', 100)),
        'past_days': int(data.get('past_days', 30)),
        'literal': data.get('literal', 'true').lower() == 'true',
        'run_scirate': data.get('run_scirate', 'false').lower() == 'true',
        'arxiv_sortby': data.get('arxiv_sortby', 'submittedDate'),
        'arxiv_sortorder': data.get('arxiv_sortorder', 'descending'),
        'sortby': sortby,
        'sortorder_rev': data.get('sortorder_rev', 'true').lower() == 'true',
        'and_or_sections': data.get('and_or_sections', '+OR+'),
        'and_or_keyauthors': data.get('and_or_keyauthors', '+OR+'),
        'and_or': data.get('and_or', '+OR+'),
        'and_or_keywords': data.get('and_or_keywords', '+OR+'),
        'keys': {
            'sections': sections,
            'keyauthors': keyauthors,
            'keywords': keywords,
        }
    }
    
# if __name__ == "__main__":
#     app.run(debug=True)

if __name__ == "__main__":
    import logging
    logging.getLogger('waitress.queue').setLevel(logging.ERROR)
    from waitress import serve
    webbrowser.open('http://localhost:'+str(app_port)+'/', new=2)
    serve(app, host="0.0.0.0", port=app_port, threads=8)