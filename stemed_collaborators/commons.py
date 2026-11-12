"""Read a member's public STEMEd+ Commons profile, so the join form can skip what Commons already knows.

Knowledge Commons' profile system answers, for any username, with the member's name, institution, ORCID iD,
academic interests, photo, and which Commons networks they belong to:

    https://stemedplus.profile.hcommons.org/api/v1/members/<username>/

This address is public but not documented, and Knowledge Commons is rewriting its profile system, so sign-up
never depends on it: when it does not answer, the form's own answers are used.
"""
import json
import urllib.error
import urllib.request
from typing import Optional, Tuple

from . import profiles

API = "https://stemedplus.profile.hcommons.org/api/v1/members/{username}/"
PROFILE = "https://stemedplus.profile.hcommons.org/members/{username}/"

OK, MISSING, UNAVAILABLE = "ok", "missing", "unavailable"


def profile_url(username: str) -> str:
    return PROFILE.format(username=username)


def fetch(username: str, timeout: float = 15) -> Tuple[str, Optional[dict]]:
    """("ok", data), ("missing", None) when Commons has no such member, or ("unavailable", None)."""
    if not username or not profiles.USERNAME.match(username):
        return MISSING, None
    req = urllib.request.Request(API.format(username=username),
                                 headers={"Accept": "application/json", "User-Agent": "stemed-collaborators"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return (MISSING, None) if exc.code == 404 else (UNAVAILABLE, None)
    except (urllib.error.URLError, OSError, ValueError):
        return UNAVAILABLE, None
    if not isinstance(data, dict) or str(data.get("username", "")).lower() != username.lower():
        return UNAVAILABLE, None
    return OK, data


def is_stemedplus_member(data: dict) -> Optional[bool]:
    """True or False when Commons says, None when it does not."""
    memberships = data.get("memberships")
    if isinstance(memberships, dict) and "STEMED+" in memberships:
        return bool(memberships["STEMED+"])
    return None


def backfill_photos(folder=None, lookup=fetch) -> list:
    """Add the Commons photo to listed profiles that have none. Returns the usernames changed."""
    import yaml
    from pathlib import Path
    folder = Path(folder or profiles.PROFILES)
    changed = []
    for path in sorted(folder.glob("*.yml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or data.get("photo"):
            continue
        status, info = lookup(path.stem)
        photo = ((info or {}).get("avatar") or "").strip() if status == OK else ""
        if profiles.is_photo_url(photo):
            data["photo"] = photo
            path.write_text(profiles.dump(data), encoding="utf-8")
            changed.append(path.stem)
    return changed


if __name__ == "__main__":
    import sys
    if sys.argv[1:] == ["--backfill-photos"]:
        done = backfill_photos()
        print("Added photos for: " + (", ".join(done) if done else "nobody"))
    else:
        print("usage: python -m stemed_collaborators.commons --backfill-photos")
