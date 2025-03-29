from urllib.parse import urlparse, urlunparse


def normalize_url(url):
    parsed_url = urlparse(url)
    scheme = parsed_url.scheme or "http"
    netloc = parsed_url.netloc or parsed_url.path
    path = parsed_url.path if parsed_url.netloc else "/"
    if not path.endswith("/"):
        path += "/"
    normalized_url = urlunparse((scheme, netloc, path, "", "", ""))
    return normalized_url

