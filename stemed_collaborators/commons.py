"""Read STEMEd+ Commons members and their public profiles.

Two public addresses on the Knowledge Commons profile system are used:

    https://stemedplus.profile.hcommons.org/members/              the STEMEd+ member directory (web page)
    https://stemedplus.profile.hcommons.org/api/v1/members/<u>/   one member's public profile (JSON)

The directory gives the list of usernames (the JSON list of all members needs a private key). Each profile
gives name, institution, ORCID iD, photo, academic interests, and which Commons networks the member is in.
Neither address is documented, and Knowledge Commons is still changing its profile system, so the build
keeps the last good copy when either stops answering (see directory.py).
"""
import html
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Callable, Iterator, List, Optional, Tuple

BASE = "https://stemedplus.profile.hcommons.org"
DIRECTORY = BASE + "/members/?per_page=96"
API = BASE + "/api/v1/members/{username}/"
PROFILE = BASE + "/members/{username}/"
EDIT_PROFILE = BASE + "/edit-profile/"

# Commons usernames are mostly letters, digits, dots, dashes, and underscores, but some hold other
# characters (for example @ or +), so anything without a slash or a space is accepted and quoted in URLs.
USERNAME = re.compile(r"^[^/\s?#]{1,100}$")
CARD_LINK = re.compile(r'<a\s+href="([^"]+)"\s+class="member-card-link"')
TOTAL = re.compile(r'class="member-count">\s*([\d,]+) member')
PREV_LINK = re.compile(r'<a\s+href="([^"]*dir=prev[^"]*)"')
NEXT_LINK = re.compile(r'<a\s+href="([^"]*cursor=[^"]*)"\s*>\s*Next')

OK, MISSING, UNAVAILABLE = "ok", "missing", "unavailable"
USER_AGENT = "stemed-collaborators (https://github.com/stemedplus/stemed-collaborators)"


def profile_url(username: str) -> str:
    return PROFILE.format(username=urllib.parse.quote(username, safe=""))


def http_get(url: str, accept: str = "application/json", timeout: float = 20) -> Tuple[int, str]:
    """(status, body). Status 0 means no answer at all."""
    req = urllib.request.Request(url, headers={"Accept": accept, "User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, ""
    except (urllib.error.URLError, OSError):
        return 0, ""


def usernames_on_page(page: str) -> List[str]:
    """Usernames of the member cards on one directory page, in page order."""
    found = []
    for href in CARD_LINK.findall(page):
        path = urllib.parse.urlparse(html.unescape(href)).path.strip("/").split("/")
        name = urllib.parse.unquote(path[-1]) if path else ""
        if len(path) >= 2 and path[-2] == "members" and USERNAME.match(name) and name not in found:
            found.append(name)
    return found


def next_page(page: str, current_url: str) -> Optional[str]:
    m = NEXT_LINK.search(page)
    return urllib.parse.urljoin(current_url, html.unescape(m.group(1))) if m else None


def directory_total(page: str) -> Optional[int]:
    """The member count the directory states ("946 members"), or None."""
    m = TOTAL.search(page)
    return int(m.group(1).replace(",", "")) if m else None


def _crawl(start: str, follow: Callable[[str, str], Optional[str]], names: List[str], get: Callable,
           max_pages: int, pause: float) -> str:
    """Read pages from start, following links with follow(page, url); add usernames to names. Returns the last URL."""
    url, seen, last = start, set(), start
    for _ in range(max_pages):
        if not url or url in seen:
            break
        seen.add(url)
        status, page = get(url, accept="text/html")
        if status != 200:
            raise RuntimeError(f"member directory answered {status or 'nothing'} at {url}")
        if directory_usernames.total is None:
            directory_usernames.total = directory_total(page)
        for name in usernames_on_page(page):
            if name not in names:
                names.append(name)
        last, url = url, follow(page, url)
        if url:
            time.sleep(pause)
    return last


def prev_page(page: str, current_url: str) -> Optional[str]:
    m = PREV_LINK.search(page)
    return urllib.parse.urljoin(current_url, html.unescape(m.group(1))) if m else None


def directory_usernames(get: Callable = http_get, max_pages: int = 200, pause: float = 0.5) -> List[str]:
    """Every username in the STEMEd+ member directory. Raises RuntimeError if the directory can't be read.

    The directory sorts members in its database but pages through them with a comparison that orders
    capital letters differently, so paging forward skips some members (among those who never signed in).
    Paging back from the last page reaches them, so both directions are read and combined.
    The count the directory states is kept in directory_usernames.total, so a run can report any gap."""
    names: List[str] = []
    directory_usernames.total = None
    last = _crawl(DIRECTORY, next_page, names, get, max_pages, pause)
    if directory_usernames.total is None or len(names) < directory_usernames.total:
        _crawl(last, prev_page, names, get, max_pages, pause)
    if not names:
        raise RuntimeError("member directory had no member cards (the page layout may have changed)")
    return names


def fetch(username: str, get: Callable = http_get) -> Tuple[str, Optional[dict]]:
    """("ok", data), ("missing", None) when Commons has no such member, or ("unavailable", None)."""
    if not username or not USERNAME.match(username):
        return MISSING, None
    status, body = get(API.format(username=urllib.parse.quote(username, safe="")))
    if status == 404:
        return MISSING, None
    if status != 200:
        return UNAVAILABLE, None
    try:
        data = json.loads(body)
    except ValueError:
        return UNAVAILABLE, None
    if not isinstance(data, dict) or str(data.get("username", "")).lower() != username.lower():
        return UNAVAILABLE, None
    return OK, data


def is_stemedplus_member(data: dict) -> Optional[bool]:
    """True or False when the profile says, None when it does not."""
    memberships = data.get("memberships")
    if isinstance(memberships, dict) and "STEMED+" in memberships:
        return bool(memberships["STEMED+"])
    return None


def interests(data: dict) -> List[str]:
    """Academic interests as plain text, in profile order, without duplicates."""
    out = []
    for item in data.get("academic_interests") or []:
        text = item.get("text") if isinstance(item, dict) else item
        text = re.sub(r"\s+", " ", html.unescape(str(text or ""))).strip()
        if text and text.lower() not in (x.lower() for x in out):
            out.append(text)
    return out


def iter_profiles(usernames: List[str], get: Callable = http_get, workers: int = 6) -> Iterator[Tuple[str, str, Optional[dict]]]:
    """(username, status, data) for each username, read a few at a time."""
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for name, (status, data) in zip(usernames, pool.map(lambda u: fetch(u, get), usernames)):
            yield name, status, data
