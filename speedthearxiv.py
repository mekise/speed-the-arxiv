import os
import re
import json
import platform
import subprocess
import yaml
import requests

try:
    import fitz as _fitz
    _PYMUPDF = True
except ImportError:
    _PYMUPDF = False

ARXIV_HEADERS = {'User-Agent': 'speed-the-arxiv/1.0 (https://github.com/mekise/speed-the-arxiv)'}
import feedparser
import asyncio
import aiohttp
import webbrowser
import datetime as dt
from urllib.parse import urljoin
from flask import Flask, render_template, request, jsonify, send_from_directory, send_file, redirect
from habanero import cn
from bs4 import BeautifulSoup

app_port = 8080
app = Flask(__name__)
CACHE_DIR = './cache'
os.makedirs(CACHE_DIR, exist_ok=True)
FAVOURITES_DIR = './favourites'
os.makedirs(FAVOURITES_DIR, exist_ok=True)
FAVOURITES_FILE = os.path.join(FAVOURITES_DIR, 'favourites.json')
NOTES_DIR = './notes'
os.makedirs(NOTES_DIR, exist_ok=True)

# Migrate legacy favourites.json to new location
_legacy = './favourites.json'
if os.path.exists(_legacy) and not os.path.exists(FAVOURITES_FILE):
    import shutil
    shutil.move(_legacy, FAVOURITES_FILE)

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

@app.route("/backup", methods=['GET'])
def backup():
    import zipfile, io
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        for folder in (FAVOURITES_DIR, NOTES_DIR, './search'):
            if not os.path.isdir(folder):
                continue
            for root, _dirs, files in os.walk(folder):
                for fname in files:
                    fpath = os.path.join(root, fname)
                    arcname = os.path.relpath(fpath, '.')
                    zf.write(fpath, arcname)
    buf.seek(0)
    timestamp = dt.datetime.now().strftime('%Y%m%d_%H%M%S')
    return send_file(buf, mimetype='application/zip',
                     as_attachment=True,
                     download_name=f'speed-the-arxiv-backup_{timestamp}.zip')

@app.route("/favourites", methods=['GET'])
def favourites():
    papers = load_favourites()
    for p in papers:
        p.setdefault('tags', [])
    all_tags = sorted({t for p in papers for t in p.get('tags', [])})
    return render_template("favourites.html", papers=papers, all_tags=all_tags)

@app.route("/update_tags", methods=['POST'])
def update_tags():
    data = request.get_json()
    arxiv_id = str(data.get('arxiv_id', '')).strip()
    if not arxiv_id:
        return jsonify({"error": "Missing arxiv_id"}), 400
    tags = [t.strip() for t in data.get('tags', []) if t.strip()]
    favs = load_favourites()
    for f in favs:
        if f['arxiv_id'] == arxiv_id:
            f['tags'] = tags
            save_favourites(favs)
            return jsonify({"tags": tags})
    return jsonify({"error": "Not found"}), 404

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

# ── PDF scanning helpers ────────────────────────────────────────────────────

# Labeled arXiv ID: "arXiv:2301.12345" or DOI form "10.48550/arXiv.2301.12345"
_ARXIV_LABELED = re.compile(
    r'(?:arXiv[:\s]+(\d{4}\.\d{4,5})(?:v\d+)?'
    r'|10\.48550/arXiv\.(\d{4}\.\d{4,5}))',
    re.IGNORECASE
)
# Generic DOI
_DOI_RE = re.compile(r'\b(10\.\d{4,9}/[^\s\]},;\"\'<>\[\)]+)', re.IGNORECASE)


def _find_ids(text):
    """Return (arxiv_id, doi) from text. arXiv ID takes precedence."""
    for m in _ARXIV_LABELED.finditer(text):
        aid = m.group(1) or m.group(2)
        return aid, None
    m = _DOI_RE.search(text)
    return None, m.group(1).rstrip('.,') if m else None


def _scan_pdf(path):
    """
    Extract arXiv ID or DOI from a PDF using a layered strategy:
      1. filename  2. PDF metadata  3. XMP metadata  4. first-page text
    Returns {'arxiv_id', 'doi', 'source'}.
    """
    stem = os.path.splitext(os.path.basename(path))[0]

    # 1. filename: covers all arXiv downloads (e.g. "2301.12345v2.pdf")
    m = re.match(r'^(\d{4}\.\d{4,5})(?:v\d+)?$', stem)
    if m:
        return {'arxiv_id': m.group(1), 'doi': None, 'source': 'filename'}

    if not _PYMUPDF:
        return {'arxiv_id': None, 'doi': None, 'source': 'unresolved'}

    fallback_doi = None
    try:
        doc = _fitz.open(path)

        # 2. Standard PDF metadata fields
        for val in (doc.metadata or {}).values():
            if not val:
                continue
            aid, doi = _find_ids(val)
            if aid:
                doc.close()
                return {'arxiv_id': aid, 'doi': None, 'source': 'pdf_metadata'}
            if doi and not fallback_doi:
                fallback_doi = doi

        # 3. XMP metadata (richer: dc:identifier, prism:doi, etc.)
        xmp = doc.get_xml_metadata() or ''
        if xmp:
            aid, doi = _find_ids(xmp)
            if aid:
                doc.close()
                return {'arxiv_id': aid, 'doi': None, 'source': 'xmp'}
            if doi and not fallback_doi:
                fallback_doi = doi

        # 4. First-page text (arXiv always stamps ID in header/footer)
        if doc.page_count > 0:
            text = doc[0].get_text()
            aid, doi = _find_ids(text)
            if aid:
                doc.close()
                return {'arxiv_id': aid, 'doi': None, 'source': 'page_text'}
            if doi and not fallback_doi:
                fallback_doi = doi

        doc.close()
    except Exception:
        pass

    src = 'page_text' if fallback_doi else 'unresolved'
    return {'arxiv_id': None, 'doi': fallback_doi, 'source': src}


def _fetch_arxiv_paper(arxiv_id):
    url = f"https://export.arxiv.org/api/query?id_list={arxiv_id}&max_results=1"
    try:
        resp = requests.get(url, headers=ARXIV_HEADERS, timeout=30)
        if resp.status_code == 200:
            feeds = feedparser.parse(resp.text)
            if feeds.entries:
                return process_entry_adhoc(feeds.entries[0])
    except Exception:
        pass
    return None


def _fetch_doi_paper(doi):
    try:
        resp = requests.get(
            f"https://api.crossref.org/works/{requests.utils.quote(doi, safe='/')}",
            headers={'User-Agent': ARXIV_HEADERS['User-Agent']}, timeout=30
        )
        if resp.status_code != 200:
            return None
        msg = resp.json().get('message', {})
        title = (msg.get('title') or [''])[0]
        authors = ', '.join(
            ' '.join(filter(None, [a.get('given'), a.get('family')]))
            for a in msg.get('author', [])
        )
        dp = ((msg.get('published') or msg.get('created') or {})
              .get('date-parts', [[]])[0])
        date = '-'.join(str(p).zfill(2) for p in dp[:3]) if dp else ''
        try:
            bibtex = format_bibtex_string(cn.content_negotiation(ids=doi, format="bibentry"))
        except Exception:
            bibtex = ''
        safe_id = 'doi_' + re.sub(r'[^\w.-]', '_', doi)
        return {
            'arxiv_id': safe_id,
            'title': title,
            'authors': authors,
            'date': date[:10],
            'abs_url': f"https://doi.org/{doi}",
            'pdf_url': f"https://doi.org/{doi}",
            'category': msg.get('type', ''),
            'summary': BeautifulSoup(msg.get('abstract') or '', 'html.parser').get_text().strip(),
            'bibtex': bibtex,
            'related_doi': doi,
            'scirate': 0,
        }
    except Exception:
        return None


@app.route("/scan_favourites", methods=['GET'])
def scan_favourites():
    existing_ids = {f['arxiv_id'] for f in load_favourites()}
    try:
        pdf_files = sorted(f for f in os.listdir(FAVOURITES_DIR) if f.lower().endswith('.pdf'))
    except OSError:
        return jsonify([])

    results = []
    for pdf_file in pdf_files:
        info = _scan_pdf(os.path.join(FAVOURITES_DIR, pdf_file))
        arxiv_id = info['arxiv_id']
        doi = info['doi']

        # DOI that encodes an arXiv ID (10.48550/arXiv.XXXX.XXXXX)
        if not arxiv_id and doi:
            m = re.match(r'10\.48550/arXiv\.(\d{4}\.\d{4,5})', doi, re.IGNORECASE)
            if m:
                arxiv_id = m.group(1)
                doi = None

        if arxiv_id:
            if arxiv_id in existing_ids:
                continue
            paper = _fetch_arxiv_paper(arxiv_id)
        elif doi:
            safe_id = 'doi_' + re.sub(r'[^\w.-]', '_', doi)
            if safe_id in existing_ids:
                continue
            paper = _fetch_doi_paper(doi)
        else:
            paper = None

        entry = paper or {
            'arxiv_id': arxiv_id or doi or '',
            'title': '', 'authors': '', 'date': '',
            'abs_url': '', 'category': '', 'summary': '', 'bibtex': '',
        }
        entry['filename'] = pdf_file
        entry['pdf_url'] = f"/local_pdf/{pdf_file}"
        entry['detection_source'] = info['source']
        entry['unresolved'] = paper is None
        results.append(entry)

    return jsonify(results)


@app.route("/import_local_paper", methods=['POST'])
def import_local_paper():
    data = request.get_json()
    arxiv_id = str(data.get('arxiv_id', '')).strip()
    if not arxiv_id:
        return jsonify({"error": "Missing arxiv_id"}), 400
    favs = load_favourites()
    if any(f['arxiv_id'] == arxiv_id for f in favs):
        return jsonify({"imported": False, "reason": "already_exists"})
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
    return jsonify({"imported": True})

@app.route("/local_pdf/<path:filename>")
def local_pdf(filename):
    return send_from_directory(os.path.abspath(FAVOURITES_DIR), filename)

# ── end PDF scanning ─────────────────────────────────────────────────────────

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
    
# ── Layer the Arxiv ──────────────────────────────────────────────────────

@app.route("/layer")
@app.route("/layer/")
def layer_home():
    user_sections = set()
    try:
        for fname in os.listdir('./search'):
            if fname.endswith('.yaml'):
                with open(os.path.join('search', fname)) as f:
                    cfg = yaml.safe_load(f)
                for s in cfg.get('keys', {}).get('sections', []):
                    user_sections.add(s)
    except Exception:
        pass
    fav_ids = {f['arxiv_id'] for f in load_favourites()}
    return render_template("layer.html", arxiv_path="", layer_page=None,
                           favourite_ids=fav_ids,
                           user_sections=sorted(user_sections))


@app.route("/layer/<path:arxiv_path>")
def layer_proxy(arxiv_path):
    arxiv_url = f"https://arxiv.org/{arxiv_path}"
    qs = request.query_string.decode()
    if qs:
        arxiv_url += "?" + qs
    try:
        resp = requests.get(arxiv_url, headers=ARXIV_HEADERS, timeout=30)
    except Exception:
        fav_ids = {f['arxiv_id'] for f in load_favourites()}
        return render_template("layer.html", arxiv_path=arxiv_path,
            layer_page={'error': 'Could not reach arxiv.org.'},
            favourite_ids=fav_ids, user_sections=[])

    ct = resp.headers.get('Content-Type', '')
    if 'text/html' not in ct:
        return redirect(arxiv_url)

    if resp.status_code != 200:
        fav_ids = {f['arxiv_id'] for f in load_favourites()}
        return render_template("layer.html", arxiv_path=arxiv_path,
            layer_page={'error': f'arxiv.org returned status {resp.status_code}.'},
            favourite_ids=fav_ids, user_sections=[])

    page = _process_layer_page(resp.text, arxiv_path)
    fav_ids = {f['arxiv_id'] for f in load_favourites()}
    return render_template("layer.html", arxiv_path=arxiv_path, layer_page=page,
                           favourite_ids=fav_ids, user_sections=[])


def _process_layer_page(html, arxiv_path):
    """Parse an arxiv HTML page and return a dict with papers, heading, nav links, and info."""
    soup = BeautifulSoup(html, 'html.parser')
    body = soup.find('body')
    if not body:
        return {'papers': [], 'heading': '', 'nav_links': [], 'page_info': '',
                'is_abstract': False}

    base_url = f"https://arxiv.org/{arxiv_path}"

    def rewrite_url(url):
        if not url or url.startswith('#') or url.startswith('mailto:'):
            return url
        abs_url = urljoin(base_url, url)
        if 'arxiv.org/' in abs_url:
            return '/layer/' + abs_url.split('arxiv.org/', 1)[1]
        return abs_url

    # Extract heading
    heading = ''
    h1 = body.find('h1')
    if h1:
        heading = h1.get_text(strip=True)
        # Clean "Title:" prefix on abstract pages
        if heading.startswith('Title:'):
            heading = ''

    # Extract navigation links (section nav on listing pages)
    nav_links = []
    for ul in body.find_all('ul'):
        links = ul.find_all('a', href=True)
        if not links:
            continue
        is_section_nav = any(
            '/list/' in (a.get('href') or '') for a in links
        )
        if is_section_nav and len(links) <= 10:
            for a in links:
                href = rewrite_url(a['href'])
                nav_links.append({'text': a.get_text(strip=True), 'url': href})
            break

    # Also capture "See recent articles" / "See new articles" links
    see_links = []
    for a in body.find_all('a', href=True):
        text = a.get_text(strip=True).lower()
        if text in ('recent', 'new') and '/list/' in (a.get('href') or ''):
            see_links.append({'text': text, 'url': rewrite_url(a['href'])})

    # Extract page info text (listing summary)
    page_info = ''
    for tag in body.find_all(['h2', 'h3']):
        text = tag.get_text(strip=True)
        if 'showing' in text.lower() or 'listing' in text.lower():
            page_info = text
            break
    # Also grab total count
    for small in body.find_all(['small', 'span']):
        text = small.get_text(strip=True)
        if 'total of' in text.lower():
            page_info = (page_info + '  -  ' + text) if page_info else text
            break

    # Extract papers
    papers = _extract_layer_papers(body, arxiv_path)
    is_abstract = arxiv_path.startswith('abs/')

    return {
        'papers': papers,
        'heading': heading,
        'nav_links': nav_links + see_links,
        'page_info': page_info,
        'is_abstract': is_abstract,
    }


def _layer_text(el, label=''):
    """Extract text from a BS4 element, stripping a leading label."""
    if el is None:
        return ''
    text = el.get_text(' ', strip=True)
    if label and text.startswith(label):
        text = text[len(label):].strip()
    return text


def _extract_layer_papers(body, arxiv_path):
    papers = []
    seen = set()

    # Listing pages: dt/dd structure (/list/...)
    for dt_tag in body.find_all('dt'):
        a = dt_tag.find('a', href=re.compile(r'/abs/\d{4}\.\d{4,5}'))
        if not a:
            continue
        m = re.search(r'(\d{4}\.\d{4,5})', a.get('href', ''))
        if not m or m.group(1) in seen:
            continue
        aid = m.group(1)
        seen.add(aid)
        dd = dt_tag.find_next_sibling('dd')
        title = _layer_text(dd.find('div', class_='list-title') if dd else None, 'Title:')
        authors = _layer_text(dd.find('div', class_='list-authors') if dd else None, 'Authors:')
        summary = _layer_text(dd.find('p', class_='mathjax') if dd else None)
        cat_el = dd.find('div', class_='list-subjects') if dd else None
        category = ''
        if cat_el:
            primary = cat_el.find('span', class_='primary-subject')
            category = primary.get_text(strip=True) if primary else ''
        papers.append(_make_layer_paper(aid, title, authors, summary, category))

    # Abstract pages: /abs/XXXX.XXXXX
    m_abs = re.match(r'abs/(\d{4}\.\d{4,5})', arxiv_path)
    if m_abs and m_abs.group(1) not in seen:
        aid = m_abs.group(1)
        seen.add(aid)
        title = _layer_text(body.find('h1', class_='title'), 'Title:')
        authors = _layer_text(body.find('div', class_='authors'), 'Authors:')
        summary = _layer_text(body.find('blockquote', class_='abstract'), 'Abstract:')
        subj = body.find('td', class_='subjects')
        category = ''
        if subj:
            primary = subj.find('span', class_='primary-subject')
            category = primary.get_text(strip=True) if primary else ''
        date = ''
        dateline = body.find('div', class_='dateline')
        if dateline:
            dm = re.search(r'(\d{1,2}\s+\w{3}\s+\d{4})', dateline.get_text())
            if dm:
                try:
                    date = dt.datetime.strptime(dm.group(1), '%d %b %Y').strftime('%Y-%m-%d')
                except (ValueError, AttributeError):
                    pass
        papers.append(_make_layer_paper(aid, title, authors, summary, category, date))

    # Search result pages: li.arxiv-result
    for li in body.find_all('li', class_='arxiv-result'):
        a = li.find('a', href=re.compile(r'/abs/\d{4}\.\d{4,5}'))
        if not a:
            continue
        m = re.search(r'(\d{4}\.\d{4,5})', a.get('href', ''))
        if not m or m.group(1) in seen:
            continue
        aid = m.group(1)
        seen.add(aid)
        title = _layer_text(li.find('p', class_='title'))
        authors = _layer_text(li.find('p', class_='authors'), 'Authors:')
        abs_el = li.find('span', class_='abstract-full') or li.find('span', class_='abstract-short')
        summary = _layer_text(abs_el)
        summary = re.sub(r'[△▽]\s*(Less|More)$', '', summary).strip()
        tags_div = li.find('div', class_='tags')
        category = ''
        if tags_div:
            first_tag = tags_div.find('span', class_='tag')
            category = first_tag.get_text(strip=True) if first_tag else ''
        papers.append(_make_layer_paper(aid, title, authors, summary, category))

    return papers


def _make_layer_paper(arxiv_id, title, authors, summary, category, date=''):
    year = '20' + arxiv_id[:2]
    first_author = 'unknown'
    if authors:
        parts = authors.split(',')[0].strip().split()
        if parts:
            first_author = re.sub(r'[^a-z]', '', parts[-1].lower()) or 'unknown'
    primary_class = category.split('(')[0].strip() if category else ''
    bibtex = (f"@article{{{first_author}{year}{arxiv_id},\n"
              f"\ttitle={{{title}}},\n"
              f"\tauthor={{{authors}}},\n"
              f"\tyear={{{year}}},\n"
              f"\teprint={{{arxiv_id}}},\n"
              f"\tarchivePrefix={{arXiv}},\n"
              f"\tprimaryClass={{{primary_class}}}\n}}")
    return {
        'arxiv_id': arxiv_id,
        'title': title,
        'authors': authors,
        'summary': summary,
        'category': category,
        'date': date,
        'abs_url': f'https://arxiv.org/abs/{arxiv_id}',
        'pdf_url': f'https://arxiv.org/pdf/{arxiv_id}',
        'bibtex': bibtex,
        'scirate': 0,
        'related_doi': '',
    }

# ── end Layer the Arxiv ─────────────────────────────────────────────────

# if __name__ == "__main__":
#     app.run(debug=True)

if __name__ == "__main__":
    import logging
    logging.getLogger('waitress.queue').setLevel(logging.ERROR)
    from waitress import serve
    webbrowser.open('http://localhost:'+str(app_port)+'/', new=2)
    serve(app, host="0.0.0.0", port=app_port, threads=8)