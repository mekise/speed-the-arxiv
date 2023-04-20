import sys
from flask import Flask, render_template
import feedparser
import webbrowser
import datetime as dt
from scirate.client import ScirateClient

app = Flask(__name__)

@app.route("/")
def index():
    allsections = False # check all categories?
    runscirate = False
    maxresults = 100 # max number of results shown
    pastdays = 365 # number of days to check from today
    ####################
    # andor vars decide how to search for keyauthors and keywords
    # they can take the value "+OR+", "+AND+", "+ANDNOT+"
    # "+OR+" -> select all the results with ANY of the keys
    # "+AND+" -> select all the results with ALL the keys
    # "+ANDNOT+" -> select all the result with none of the keys
    andor_sections = "+OR+"
    andor_keyauthors = "+OR+"
    andor = "+OR+"
    andor_keywords = "+OR+"
    ####################
    with open('keys.txt', 'r') as file:
        stringkeys = file.read()
    sections = stringkeys.partition("SECTIONS:\n")[2].partition("\n")[0].split(',')
    keyauthors = stringkeys.partition("KEYAUTHORS:\n")[2].partition("\n")[0].split(',')
    keywords = stringkeys.partition("KEYWORDS:\n")[2].partition("\n")[0].split(',')
    if allsections:
        query = andor_keyauthors.join("au:"+keyauthor for keyauthor in keyauthors)
        query += andor
        query += andor_keywords.join("all:"+"\""+keyword+"\"" for keyword in keywords)
    else:
        query = andor_sections.join("cat:"+section for section in sections)
        query += "+AND+%28" # "+AND+("
        query += andor_keyauthors.join("au:"+keyauthor for keyauthor in keyauthors)
        query += andor
        query += andor_keywords.join("all:"+"\""+keyword+"\"" for keyword in keywords)
        query += "%29" # ")"
    query = query.replace(" ", "%20")
    feeds = feedparser.parse("https://export.arxiv.org/api/query?search_query="+query+"&start=0&max_results="+str(maxresults)+"&sortBy=submittedDate&sortOrder=descending")
    papers = []
    for entry in feeds.entries:
        checkdate = [ele for ele in entry.updated[0:10].split('-')]
        if dt.date.today()-dt.date(int(checkdate[0]),int(checkdate[1]),int(checkdate[2]))<=dt.timedelta(days=pastdays):
            title = entry.title
            authors = ", ".join(author.name for author in entry.authors)
            summary = entry.summary
            date = entry.updated[0:10]
            category = ", ".join(ele for ele in entry.category.split('.'))
            pdf_url = entry.link
            scirate = 0
            if runscirate:
                scirate = ScirateClient().paper(entry.id.partition("http://arxiv.org/abs/")[2]).scites
            papers.append({
                "title": title,
                "authors": authors,
                "summary": summary,
                "date": date,
                "category": category,
                "pdf_url": pdf_url,
                "scirate": scirate
            })
    return render_template("index.html", papers=papers, runscirate=runscirate)

webbrowser.open('http://localhost:5000/', new=2)

if __name__ == "__main__":
    app.run()
