# What do i want
# I want to give this a url and I want it to crawl throght the site and find
# the career site
# if I find the career site then I want it to prompt me with what kind of job
# I am looking for and it will find it

# I want it to have a heuristic of looking for the words jobs or careers

# from html.parser import HTMLParser
from crawler import crawler
from urllib.parse import urlparse

URL = "https://ronb.co"

url_list = []
visited_pages = set()  # Use a set for visited pages

parse_url = urlparse(URL)
base_domain = parse_url.netloc

crawler(URL, visited_pages, url_list, base_domain)

print("-->>", visited_pages)
