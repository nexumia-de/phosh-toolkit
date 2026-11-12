"""Which redirect http.Client follows, and how. The client follows
redirects itself instead of libsoup, so that headers scoped to an origin
(the proxy's cookie and Basic auth, the app's Authorization) never reach
another origin. No GTK."""
from urllib.parse import urljoin, urlsplit

MAX_HOPS = 20

REDIRECTS = (301, 302, 303, 307, 308)

# Headers the app sets that carry a secret: dropped when a redirect leaves
# the origin they were meant for.
SECRET_HEADERS = ("authorization", "cookie", "proxy-authorization",
                  "x-emby-authorization", "x-emby-token",
                  "x-mediabrowser-token")


def origin(url):
    """"https://host:port" of a URL: the key of Client.cookies and
    Client.proxy_auth."""
    parts = urlsplit(url)
    port = parts.port or {"http": 80, "https": 443}.get(parts.scheme, 0)
    return f"{parts.scheme}://{(parts.hostname or '').lower()}:{port}"


def next_hop(method, url, status, location):
    """(method, url) of the request a redirect asks for, or None if the
    client hands the redirect to the caller, as libsoup does. Followed:
    301/302 for GET and HEAD, and for POST as GET; 303 for any method as
    GET (HEAD stays HEAD); 307/308 for GET and HEAD. Not followed: every
    other method, no Location, a scheme other than http(s). The next hop
    never has a body, so a body is never resent to a redirect target."""
    if status not in REDIRECTS or not location:
        return None
    target = urljoin(url, location)
    if urlsplit(target).scheme not in ("http", "https"):
        return None
    if method in ("GET", "HEAD"):
        return method, target
    if status == 303 or (status in (301, 302) and method == "POST"):
        return "GET", target
    return None


def carried_headers(headers, from_url, to_url):
    """The app's headers for the next hop: all of them within one origin,
    without SECRET_HEADERS across origins."""
    headers = dict(headers or {})
    if origin(from_url) == origin(to_url):
        return headers
    return {name: value for name, value in headers.items()
            if name.lower() not in SECRET_HEADERS}
