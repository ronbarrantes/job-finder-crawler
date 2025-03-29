# What do i want
# I want to give this a url and I want it to crawl throght the site and find
# the career site
# if I find the career site then I want it to prompt me with what kind of job
# I am looking for and it will find it

# I want it to have a heuristic of looking for the words jobs or careers

# from html.parser import HTMLParser
from crawler import start_crawler
from utils.cli_arguments import parse_arguments
from utils.normalize_url import normalize_url


def main():
    args = parse_arguments()
    visited_pages = set()

    url = normalize_url(args.url)
    start_crawler(url, visited_pages)
    print("-->>", visited_pages)


if __name__ == "__main__":
    main()
