import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin


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
