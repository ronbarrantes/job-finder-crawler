from collections import deque
import requests
import random
import time
import re
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin, ParseResult
from concurrent.futures import ThreadPoolExecutor, wait
from threading import Lock, Semaphore
from urllib.robotparser import RobotFileParser

# GLOBALS
lock = Lock()  # Lock for thread-safe access to shared resources
semaphore = Semaphore(10)  # Limit the number of concurrent threads
found_career_page = False  # Flag to signal when a career page is found
career_page_url = None  # Store the career page URL
# Define the maximum depth for crawling
MAX_DEPTH = 3  # Adjust this value as needed

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
]

JOB_KEYWORDS = ["career", "careers", "job", "jobs", "work", "employment", "vacancy", "vacancies"]

def start_crawler(start_url: str, visited_pages: set, max_threads: int = 5) -> str:
    """
    Start the BFS-based crawler with multithreading and max depth.
    """
    global career_page_url

    base_domain = urlparse(start_url).netloc
    queue = deque([(start_url, 0)])  # Initialize the queue with the start URL and depth 0
    tasks = []  # Track tasks submitted to the executor
    robots_parsers = {}  # Cache for robots.txt parsers

    # Create a session object for reuse
    session = requests.Session()
    session.headers.update({"User-Agent": random.choice(USER_AGENTS)})

    with ThreadPoolExecutor(max_threads) as executor:
        while queue and not found_career_page:
            current_url, current_depth = queue.popleft()  # Get the next URL and its depth from the queue

            # Skip if the URL has already been visited
            with lock:
                if current_url in visited_pages:
                    continue
                visited_pages.add(current_url)

            # Stop processing if the max depth is reached
            if current_depth > MAX_DEPTH:
                print(f"Reached max depth at {current_url}")
                continue

            # Submit the task to process the page
            task = executor.submit(
                process_page_bfs,
                current_url,
                current_depth,
                session,
                queue,
                visited_pages,
                base_domain,
                robots_parsers,
            )
            tasks.append(task)

        # Wait for all tasks to complete or until a career page is found
        wait(tasks)

        # If a career page is found, shut down the executor immediately
        if found_career_page:
            executor.shutdown(wait=False)

    # Return the career page URL if found, otherwise return a fallback message
    if career_page_url:
        return career_page_url
    else:
        return "No career page found."


def process_page_bfs(
    url: str,
    depth: int,
    session: requests.Session,
    queue: deque,
    visited_pages: set,
    base_domain: str,
    robots_parsers: dict,
):
    """
    Process a single page in the BFS crawl, respecting robots.txt and max depth.
    """
    global found_career_page, career_page_url

    # Stop processing if a career page has already been found
    if found_career_page:
        return

    headers = {"User-Agent": random.choice(USER_AGENTS)}
    user_agent = headers["User-Agent"]

    # Check robots.txt before making the request
    if not is_allowed_by_robots(url, user_agent, robots_parsers):
        print(f"Blocked by robots.txt: {url}")
        return

    try:
        with semaphore:  # Limit the number of concurrent threads
            time.sleep(random.uniform(1, 3))  # Simulate human-like delays
            res = session.get(url, headers=headers, timeout=5)
            res.raise_for_status()
    except requests.RequestException as e:
        print(f"Failed to fetch {url}: {e}")
        return

    soup = BeautifulSoup(res.content, "html.parser")
    print(f"Crawling {url} at depth {depth}")

    all_herfs = soup.find_all("a", href=True)

    for link in all_herfs:
        href = link.get("href")
        if not href:
            continue

        full_url = urljoin(url, href)
        parsed_url = urlparse(full_url)

        # Check if the link is a career page
        if is_career_page(parsed_url, link.text):
            print(f"Found the career page: {full_url}")
            with lock:
                career_page_url = full_url
                found_career_page = True  # Signal that a career page is found
            return

        # If not a career page, add the URL and depth to the queue for further crawling
        if is_valid_url(parsed_url, base_domain):
            with lock:
                if full_url not in visited_pages and not found_career_page:
                    print(f"Discovered: {full_url}")
                    queue.append((full_url, depth + 1))


def is_career_page(url: ParseResult, link_text: str) -> bool:
    """
    Check if the subdomain, full URL, or link text contains any job-related keywords.
    """
    subdomain = url.netloc.lower()
    full_url = f"{url.netloc}{url.path}".lower()
    link_text_lower = link_text.lower()

    for keyword in JOB_KEYWORDS:
        keyword_pattern = rf"\b{re.escape(keyword)}\b"
        if (re.search(keyword_pattern, subdomain) or
            re.search(keyword_pattern, full_url) or
            re.search(keyword_pattern, link_text_lower)):
            return True
    return False

def is_valid_url(parsed_url: ParseResult, base_domain: str) -> bool:
    """
    Check if the URL is valid and belongs to the same domain or subdomain.
    """
    return parsed_url.netloc and base_domain in parsed_url.netloc


def is_allowed_by_robots(url: str, user_agent: str, robots_parsers: dict) -> bool:
    """
    Check if the URL is allowed to be crawled based on robots.txt.
    """
    parsed_url = urlparse(url)
    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

    # Check if the robots.txt parser for this domain is already loaded
    if base_url not in robots_parsers:
        robots_url = urljoin(base_url, "/robots.txt")
        rp = RobotFileParser()
        try:
            rp.set_url(robots_url)
            rp.read()
        except Exception as e:
            print(f"Failed to fetch robots.txt from {robots_url}: {e}")
            # If robots.txt cannot be fetched, assume crawling is allowed
            robots_parsers[base_url] = None
            return True
        robots_parsers[base_url] = rp

    rp = robots_parsers[base_url]
    if rp is None:
        return True  # Assume allowed if robots.txt couldn't be fetched
    return rp.can_fetch(user_agent, url)


# import requests
# import random
# import time
# from bs4 import BeautifulSoup
# from urllib.parse import urlparse, urljoin
# from concurrent.futures import wait, ThreadPoolExecutor
# from threading import Lock, Semaphore, Event
# from urllib.robotparser import RobotFileParser

# # List of User-Agents to rotate (pretend to be a real browser)
# USER_AGENTS = [
#     "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
#     "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
#     "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
# ]

# # Lock for thread-safe access to shared resources
# lock = Lock()

# # Semaphore to limit the number of concurrent threads
# semaphore = Semaphore(10)  # Adjust the value as needed

# # Define a global event to signal when a jobs page is found
# found_jobs_page = Event()

# # Define the maximum depth for crawling
# MAX_DEPTH = 3  # Adjust this value as needed

# # List of keywords to identify jobs or careers pages
# JOB_KEYWORDS = ["career", "careers", "job", "jobs", "work", "employment", "vacancy", "vacancies"]

# def is_allowed_by_robots(url: str, user_agent: str, robots_parsers: dict) -> bool:
#     """
#     Check if the URL is allowed to be crawled based on robots.txt.
#     """
#     parsed_url = urlparse(url)
#     base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

#     # Check if the robots.txt parser for this domain is already loaded
#     if base_url not in robots_parsers:
#         robots_url = urljoin(base_url, "/robots.txt")
#         rp = RobotFileParser()
#         try:
#             rp.set_url(robots_url)
#             rp.read()
#         except Exception as e:
#             print(f"Failed to fetch robots.txt from {robots_url}: {e}")
#             # If robots.txt cannot be fetched, assume crawling is allowed
#             robots_parsers[base_url] = None
#             return True
#         robots_parsers[base_url] = rp

#     rp = robots_parsers[base_url]
#     if rp is None:
#         return True  # Assume allowed if robots.txt couldn't be fetched
#     return rp.can_fetch(user_agent, url)

# def is_jobs_page(url: str, link_text: str) -> bool:
#     """
#     Check if the URL or link text contains any job-related keywords.
#     """
#     url_lower = url.lower()
#     link_text_lower = link_text.lower()
#     for keyword in JOB_KEYWORDS:
#         if keyword in url_lower or keyword in link_text_lower:
#             return True
#     return False

# # Shared variable to store the careers page URL
# careers_page_url = None

# def fetch_page(url: str, session: requests.Session, visited_pages: set, base_domain: str, executor: ThreadPoolExecutor, tasks: list, robots_parsers: dict, depth: int):
#     global careers_page_url

#     if depth > MAX_DEPTH:
#         print(f"Reached max depth at {url}")
#         return

#     # Stop processing if a jobs page has already been found
#     if found_jobs_page.is_set():
#         return

#     with lock:
#         if url in visited_pages:
#             return
#         visited_pages.add(url)

#     # Check robots.txt before making the request
#     user_agent = session.headers["User-Agent"]
#     if not is_allowed_by_robots(url, user_agent, robots_parsers):
#         print(f"Blocked by robots.txt: {url}")
#         return

#     try:
#         time.sleep(random.uniform(1, 3))  # Simulate human-like delays
#         res = session.get(url, timeout=5)
#         res.raise_for_status()
#     except requests.RequestException as e:
#         print(f"Failed to fetch {url}: {e}")
#         return

#     soup = BeautifulSoup(res.content, "html.parser")
#     print(f"Crawling {url} at depth {depth}")

#     all_herfs = soup.find_all("a", href=True)

#     for link in all_herfs:
#         href = link.get("href")
#         if not href:
#             continue  # Skip links without an href attribute

#         full_url = urljoin(url, href)
#         parsed_url = urlparse(full_url)
#         link_text = link.get_text(strip=True)

#         # Allow subdomains by checking if the base domain is part of the netloc
#         if parsed_url.netloc and base_domain in parsed_url.netloc:
#             # Check if the link is a jobs or careers page
#             if is_jobs_page(full_url, link_text):
#                 print(f"Jobs or careers page found: {full_url}")
#                 with lock:
#                     careers_page_url = full_url  # Store the careers page URL
#                 found_jobs_page.set()  # Signal that a jobs page has been found
#                 return  # Stop further crawling

#             # If not a jobs page, continue crawling
#             with lock:
#                 if full_url not in visited_pages and not found_jobs_page.is_set():
#                     print(f"Discovered: {full_url}")
#                     # Submit the task to the executor and track it
#                     task = executor.submit(fetch_page, full_url, session, visited_pages, base_domain, executor, tasks, robots_parsers, depth + 1)
#                     tasks.append(task)



# def start_crawler(start_url: str, visited_pages: set, max_threads: int = 5) -> str:
#     global careers_page_url

#     base_domain = urlparse(start_url).netloc
#     tasks = []
#     robots_parsers = {}  # Cache for robots.txt parsers

#     # Create a session object
#     session = requests.Session()
#     session.headers.update({"User-Agent": random.choice(USER_AGENTS)})

#     with ThreadPoolExecutor(max_threads) as executor:
#         # Start crawling with the initial URL at depth 0
#         initial_task = executor.submit(fetch_page, start_url, session, visited_pages, base_domain, executor, tasks, robots_parsers, depth=0)
#         tasks.append(initial_task)

#         # Wait for all tasks to complete or until a jobs page is found
#         wait(tasks)

#     # Return the careers page URL if found, otherwise return a fallback message
#     if careers_page_url:
#         return careers_page_url
#     else:
#         return "No jobs or careers page found."