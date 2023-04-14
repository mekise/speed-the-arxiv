import sys
from flask import Flask, render_template
import feedparser
import webbrowser
import datetime as dt

app = Flask(__name__)

@app.route("/")
def index():
    allsections = False
    maxresults = 200
    pastdays = 365
    with open('keys.txt', 'r') as file:
        stringkeys = file.read()
    sections = stringkeys.partition("SECTIONS:\n")[2].partition("\n")[0].split(',')
    keyauthors = stringkeys.partition("KEYAUTHORS:\n")[2].partition("\n")[0].split(',')
    keywords = stringkeys.partition("KEYWORDS:\n")[2].partition("\n")[0].split(',')
    if allsections:
        query = "+OR+".join("au:"+keyauthor for keyauthor in keyauthors)
        query += "+OR+"
        query += "+OR+".join("all:"+"\""+keyword+"\"" for keyword in keywords)
    else:
        query = "+OR+".join("cat:"+section for section in sections)
        query += "+AND+%28" # +AND+(
        query += "+OR+".join("au:"+keyauthor for keyauthor in keyauthors)
        query += "+OR+"
        query += "+OR+".join("all:"+"\""+keyword+"\"" for keyword in keywords)
        query += "%29" # )
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
            category = entry.category
            pdf_url = entry.link
            papers.append({
                "title": title,
                "authors": authors,
                "summary": summary,
                "date": date,
                "category": ", ".join(ele for ele in category.split('.')),
                "pdf_url": pdf_url
            })
    return render_template("index.html", papers=papers)

webbrowser.open('http://localhost:5000/', new=2)

if __name__ == "__main__":
    app.run(debug='off')