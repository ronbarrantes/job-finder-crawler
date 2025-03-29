# What do i want
# I want to give this a url and I want it to crawl throght the site and find
# the career site
# if I find the career site then I want it to prompt me with what kind of job
# I am looking for and it will find it

# I want it to have a heuristic of looking for the words jobs or careers

# from html.parser import HTMLParser
import requests
from bs4 import BeautifulSoup

URL = "https://ronb.co"

url_list = []
visited_pages = {}


def crawler(url, visited_pages):
    res = requests.get(url)
    soup = BeautifulSoup(res.content, "html.parser")

    print(f"Status Code: {res.status_code}")

    print("\n Respond content:")

    print(soup.find_all("a"))

    for link in soup.find_all("a"):
        print(link.get("href"))
        url_list.append(link.get("href"))


crawler(URL, visited_pages)
