import yaml
from flask import Flask, render_template
import requests
import feedparser
import re
import webbrowser
import datetime as dt

app = Flask(__name__)

@app.route("/")
def index():
    with open('config.yaml', 'r') as file:
        config = yaml.safe_load(file)
    max_results = config['max_results']
    past_days = config['past_days']
    all_sections = config['all_sections']
    literal = config['literal']
    run_scirate = config['run_scirate']
    and_or_sections = config['and_or_sections']
    and_or_keyauthors = config['and_or_keyauthors']
    and_or = config['and_or']
    and_or_keywords = config['and_or_keywords']
    sections = config['keys']['sections']
    keyauthors = config['keys']['keyauthors']
    keywords = config['keys']['keywords']
    query_sections = [f"cat:{section}" for section in sections]
    query_keyauthors = [f"au:{keyauthor}" for keyauthor in keyauthors]
    if literal:
        query_keywords = [f"all:\"{keyword}\"" for keyword in keywords]
    else:
        query_keywords = [f"all:{keyword}" for keyword in keywords]
    if all_sections:
        query = and_or_keyauthors.join(query_keyauthors) + and_or + and_or_keywords.join(query_keywords)
    else:
        query = and_or_sections.join(query_sections) + "+AND+%28" + and_or_keyauthors.join(query_keyauthors) + and_or + and_or_keywords.join(query_keywords) + "%29"
    query = query.replace(" ", "%20")
    url = f"https://export.arxiv.org/api/query?search_query={query}&start=0&max_results={max_results}&sortBy=submittedDate&sortOrder=descending"
    response = requests.get(url)
    if response.status_code == 200:
        feeds = feedparser.parse(response.text)
        papers = []
        for entry in feeds.entries:
            paper = process_entry(entry, past_days, run_scirate)
            if paper:
                papers.append(paper)
        return render_template("index.html", papers=papers, run_scirate=run_scirate)
    else:
        pass

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
            response = requests.get("https://scirate.com/arxiv/"+entry.id.partition("http://arxiv.org/abs/")[2])
            if response.status_code == 200:
                string_to_parse = feedparser.parse(response.text)['feed']['summary']
                scirate = re.findall('<button class="btn btn-default count">\\s*(\\d+)\\s*<\\/button', string_to_parse)[0]
            else:
                scirate = "-"
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

webbrowser.open('http://localhost:5000/', new=2)
if __name__ == "__main__":
    app.run()