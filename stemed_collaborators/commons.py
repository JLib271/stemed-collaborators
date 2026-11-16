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

USERNAME = re.compile(r"^[A-Za-z0-9_.-]{1,60}$")
CARD_LINK = re.compile(r'<a\s+href="([^"]+)"\s+class="member-card-link"')
NEXT_LINK = re.compile(r'<a\s+href="([^"]*cursor=[^"]*)"\s*>\s*Next')

OK, MISSING, UNAVAILABLE = "ok", "missing", "unavailable"
USER_AGENT = "stemed-collaborators (https://github.com/JLib271/stemed-collaborators)"


def profile_url(username: str) -> str:
    return PROFILE.format(username=username)


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
        if len(path) >= 2 and path[-2] == "members" and USERNAME.match(path[-1]) and path[-1] not in found:
            found.append(path[-1])
    return found


def next_page(page: str, current_url: str) -> Optional[str]:
    m = NEXT_LINK.search(page)
    return urllib.parse.urljoin(current_url, html.unescape(m.group(1))) if m else None


def directory_usernames(get: Callable = http_get, max_pages: int = 200, pause: float = 0.5) -> List[str]:
    """Every username in the STEMEd+ member directory. Raises RuntimeError if the directory can't be read."""
    url, seen, names = DIRECTORY, set(), []
    for _ in range(max_pages):
        if url in seen:
            break
        seen.add(url)
        status, page = get(url, accept="text/html")
        if status != 200:
            raise RuntimeError(f"member directory answered {status or 'nothing'} at {url}")
        for name in usernames_on_page(page):
            if name not in names:
                names.append(name)
        url = next_page(page, url)
        if not url:
            break
        time.sleep(pause)
    if not names:
        raise RuntimeError("member directory had no member cards (the page layout may have changed)")
    return names


def fetch(username: str, get: Callable = http_get) -> Tuple[str, Optional[dict]]:
    """("ok", data), ("missing", None) when Commons has no such member, or ("unavailable", None)."""
    if not username or not USERNAME.match(username):
        return MISSING, None
    status, body = get(API.format(username=urllib.parse.quote(username)))
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
