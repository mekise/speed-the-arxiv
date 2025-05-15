import os
import platform
import subprocess
import yaml
import requests
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

@app.route("/")
def index():
    searches = [os.path.splitext(file)[0] for file in os.listdir('./search') if file.endswith('.yaml')]
    searches.sort(key=lambda x: os.path.getmtime('./search/'+x+'.yaml'), reverse=True)
    search_list = []
    for search in searches:
        search_list.append(read_config(search))
    return render_template("index.html", search_list=search_list)

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/doi", methods=['POST'])
def doi():
    searches = [os.path.splitext(file)[0] for file in os.listdir('./search') if file.endswith('.yaml')]
    searches.sort(key=lambda x: os.path.getmtime('./search/'+x+'.yaml'), reverse=True)
    search_list = []
    for search in searches:
        search_list.append(read_config(search))
    if request.method == "POST":
        search_query = request.form['search_query']
        bibtex = cn.content_negotiation(ids = search_query, format = "bibentry")
        bibtex = format_bibtex_string(bibtex)
        return render_template('index.html', search_list=search_list, bibtex=bibtex)

@app.route("/search", methods=['POST'])
def search():
    if request.method == "POST":
        data = request.get_json()
    config = read_config(data['search'])
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
    response = requests.get(url)
    if response.status_code == 200:
        feeds = feedparser.parse(response.text)
        arxiv_ids = [entry.id.split('/')[-1] for entry in feeds.entries]
        scirates = asyncio.run(get_scirates_async(arxiv_ids))
        papers = []
        for i, entry in enumerate(feeds.entries):
            paper = process_entry(entry, config['past_days'], scirates[i] if config['run_scirate'] else 0)
            if paper:
                papers.append(paper)
        papers.sort(key=lambda x:tuple([x[ele] for ele in config['sortby']]), reverse=config['sortorder_rev'])
        return render_template("search.html", papers=papers, keyauthors=[keyauthor for keyauthor in config["keyauthors"]], keywords=[keyword for keyword in config["keywords"]], search_name=config['name'], run_scirate=config['run_scirate'])
    else:
        pass

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

async def fetch_scirate(session, arxiv_id):
    url = f"https://scirate.com/arxiv/{arxiv_id}"
    try:
        async with session.get(url) as response:
            html = await response.text()
            soup = BeautifulSoup(html, "html.parser")
            btn = soup.find("button", {"class": "btn btn-default count"})
            return int(btn.text.strip()) if btn else 0
    except:
        return -1
    
async def get_scirates_async(arxiv_ids):
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_scirate(session, arxiv_id) for arxiv_id in arxiv_ids]
        return await asyncio.gather(*tasks)
    
def process_entry(entry, past_days, scirate):
    checkdate = entry.updated[0:10]
    entry_date = dt.date.fromisoformat(checkdate)
    if dt.date.today() - entry_date <= dt.timedelta(days=past_days):
        return {
            "title": entry.title,
            "authors": ", ".join(author.name for author in entry.authors),
            "summary": entry.summary,
            "date": checkdate,
            "category": ", ".join(entry.category.split('.')),
            "pdf_url": entry.link,
            "scirate": scirate
        }
    return None
    
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
    
# if __name__ == "__main__":
#     app.run(debug=True)

if __name__ == "__main__":
    from waitress import serve
    webbrowser.open('http://localhost:'+str(app_port)+'/', new=2)
    serve(app, host="0.0.0.0", port=app_port)