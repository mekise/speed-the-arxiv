import sys
import os
import platform
import subprocess
import yaml
from flask import Flask, render_template, request, jsonify
import requests
import feedparser
import re
import webbrowser
import datetime as dt

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
        papers = []
        for entry in feeds.entries:
            paper = process_entry(entry, config['past_days'], config['run_scirate'])
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

def parse_scirate(entry):
    scirate = 0
    response = requests.get("https://scirate.com/arxiv/"+entry.id.partition("http://arxiv.org/abs/")[2])
    if response.status_code == 200:
        string_to_parse = feedparser.parse(response.text)['feed']['summary']
        scirate = re.findall('<button class="btn btn-default count">\\s*(\\d+)\\s*<\\/button', string_to_parse)[0]
    else:
        scirate = -1
    return int(scirate)

def process_entry(entry, past_days, run_scirate):
    checkdate = [ele for ele in entry.updated[0:10].split('-')]
    if dt.date.today() - dt.date(int(checkdate[0]), int(checkdate[1]), int(checkdate[2])) <= dt.timedelta(days=past_days):
        title = entry.title
        authors = ", ".join(author.name for author in entry.authors)
        summary = entry.summary
        date = entry.updated[0:10]
        category = ", ".join(ele for ele in entry.category.split('.'))
        pdf_url = entry.link
        scirate = 0
        if run_scirate:
            scirate = parse_scirate(entry)
        return {
            "title": title,
            "authors": authors,
            "summary": summary,
            "date": date,
            "category": category,
            "pdf_url": pdf_url,
            "scirate": scirate
        }
    else:
        return None

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