import requests
import random
import time
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
from concurrent.futures import wait, ThreadPoolExecutor
from threading import Lock, Semaphore, Event
from urllib.robotparser import RobotFileParser

# List of User-Agents to rotate (pretend to be a real browser)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
]

# Lock for thread-safe access to shared resources
lock = Lock()

# Semaphore to limit the number of concurrent threads
semaphore = Semaphore(10)  # Adjust the value as needed

# Define a global event to signal when a jobs page is found
found_jobs_page = Event()

# Define the maximum depth for crawling
MAX_DEPTH = 3  # Adjust this value as needed

# List of keywords to identify jobs or careers pages
JOB_KEYWORDS = ["career", "careers", "job", "jobs", "work", "employment", "vacancy", "vacancies"]

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

def is_jobs_page(url: str, link_text: str) -> bool:
    """
    Check if the URL or link text contains any job-related keywords.
    """
    url_lower = url.lower()
    link_text_lower = link_text.lower()
    for keyword in JOB_KEYWORDS:
        if keyword in url_lower or keyword in link_text_lower:
            return True
    return False

def fetch_page(url: str, session: requests.Session, visited_pages: set, base_domain: str, executor: ThreadPoolExecutor, tasks: list, robots_parsers: dict, depth: int):
    if depth > MAX_DEPTH:
        print(f"Reached max depth at {url}")
        return

    # Stop processing if a jobs page has already been found
    if found_jobs_page.is_set():
        return

    with lock:
        if url in visited_pages:
            return
        visited_pages.add(url)

    # Check robots.txt before making the request
    user_agent = session.headers["User-Agent"]
    if not is_allowed_by_robots(url, user_agent, robots_parsers):
        print(f"Blocked by robots.txt: {url}")
        return

    try:
        time.sleep(random.uniform(1, 3))  # Simulate human-like delays
        res = session.get(url, timeout=5)
        res.raise_for_status()
    except requests.RequestException as e:
        print(f"Failed to fetch {url}: {e}")
        return

    soup = BeautifulSoup(res.content, "html.parser")
    print(f"Crawling {url} at depth {depth}")

    all_herfs = soup.find_all("a", href=True)

    for link in all_herfs:
        href = link.get("href")
        full_url = urljoin(url, href)
        parsed_url = urlparse(full_url)
        link_text = link.get_text(strip=True)

        if parsed_url.netloc and parsed_url.netloc.endswith(base_domain):
            # Check if the link is a jobs or careers page
            if is_jobs_page(full_url, link_text):
                print(f"Jobs or careers page found: {full_url}")
                found_jobs_page.set()  # Signal that a jobs page has been found
                return  # Stop further crawling

            with lock:
                if full_url not in visited_pages and not found_jobs_page.is_set():
                    print(f"Discovered: {full_url}")
                    # Submit the task to the executor and track it
                    task = executor.submit(fetch_page, full_url, session, visited_pages, base_domain, executor, tasks, robots_parsers, depth + 1)
                    tasks.append(task)


def start_crawler(start_url: str, visited_pages: set, max_threads: int = 5):
    base_domain = urlparse(start_url).netloc
    tasks = []
    robots_parsers = {}  # Cache for robots.txt parsers

    # Create a session object
    session = requests.Session()
    session.headers.update({"User-Agent": random.choice(USER_AGENTS)})

    with ThreadPoolExecutor(max_threads) as executor:
        # Start crawling with the initial URL at depth 0
        initial_task = executor.submit(fetch_page, start_url, session, visited_pages, base_domain, executor, tasks, robots_parsers, depth=0)
        tasks.append(initial_task)

        # Wait for all tasks to complete or until a jobs page is found
        wait(tasks)

    # If no jobs or careers page is found, output a message
    if not found_jobs_page.is_set():
        print("No jobs or careers page found.")