import requests
import random
import time
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin

# from concurrent.futures import ThreadPoolExecutor

# List of User-Agents to rotate (pretend to be a real browser)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
]

def crawler(url: str, visited_pages: set, url_list: list, base_domain: str):
    if url in visited_pages:
        return  # does not revisit the same page

    visited_pages.add(url)

    try:
        res = requests.get(url, timeout=5)
        soup = BeautifulSoup(res.content, "html.parser")
    except requests.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return

    print(f"Status Code: {res.status_code} for {url}")

    for link in soup.find_all("a", href=True):
        href = link.get("href")
        full_url = urljoin(url, href)

        parsed_url = urlparse(full_url)

        if parsed_url.netloc and parsed_url.netloc.endswith(base_domain):
            if full_url not in visited_pages:
                print(f"Discovered: {full_url}")
                url_list.append(full_url)


def fetch_page(url: str, visited_pages: set, base_domain: str):
    if url in visited_pages:
        return

    visited_pages.add(url)

    headers = {"User-Agent": random.choice(USER_AGENTS)}

    try:
        time.sleep(random.uniform(1, 3))

        res = requests.get(url, headers=headers, timeout=5)
        res.raise_for_status()

    except requests.RequestException as e:
        print(f"Failed to fetch {url}: {e}")
        return

    soup = BeautifulSoup(res.content, "html.parser")
    print(f"Crawling {url}")

    all_herfs = soup.find_all("a", href=True)

    

    for link in all_herfs:
        href = link.get("href")
        full_url = urljoin(url, href)
        parsed_url = urlparse(full_url)

        # if parsed_url.scheme in {"http", "https"} and parsed_url.netloc.endswith(
        #     base_domain
        # ):

        # if parsed_url.netloc and parsed_url.netloc.endswith(base_domain):
        #     print("full url-->", full_url)
        #     executor.submit(fetch_page, full_url, visited_pages, base_domain, executor)
        if parsed_url.netloc and parsed_url.netloc.endswith(base_domain):
            if full_url not in visited_pages:
                print(f"Discovered: {full_url}")
                fetch_page(full_url, visited_pages, base_domain)
                # url_list.append(full_url)


def start_crawler(start_url: str, visited_pages: set, max_threads: int = 5):
    base_domain = urlparse(start_url).netloc

    fetch_page(start_url, visited_pages, base_domain)
