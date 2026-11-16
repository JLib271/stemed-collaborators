"""Turn STEMEd+ Commons profiles into the cards on the Find Collaborators page.

    python -m stemed_collaborators --refresh      read Commons and update data/collaborators.json

Who gets a card (config/site.json, "listing"):
  * The member is in the STEMEd+ member directory and their profile has at least one academic interest
    besides the opt-in interest.
  * When "opt_in_required" is true, their academic interests must also include the opt-in interest
    (for example "open to collaboration"). While it is false (preview), everyone with interests counts as
    opted in, and the page says so.
  * Usernames in "exclude" never get a card (for anyone who asks to be left out).

Only public profile fields are kept: name, username, institution, ORCID iD, photo, and interests.

The last good copy stays in data/collaborators.json. A refresh replaces it only when Commons answered for
most members, so a Commons outage never empties the page.
"""
import datetime as dt
import json
import re
from pathlib import Path
from typing import Callable, Iterable, List, Optional, Tuple

from . import commons

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "collaborators.json"
CONFIG = ROOT / "config" / "site.json"

MIN_ANSWERED = 0.8      # share of profiles that must answer for a refresh to count
MIN_KEPT = 0.5          # a refresh may not drop below half of the cards in the last good copy
PHOTO = re.compile(r"^https://[^\s\"'<>]+$")


def load_config(path: Path = CONFIG) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def listing_rules(config: dict) -> Tuple[bool, str, set]:
    rules = config.get("listing") or {}
    return (bool(rules.get("opt_in_required")),
            str(rules.get("opt_in_interest") or "open to collaboration").strip(),
            {str(u).lower() for u in rules.get("exclude") or []})


def same(a: str, b: str) -> bool:
    return re.sub(r"[^a-z0-9]+", " ", a.lower()).strip() == re.sub(r"[^a-z0-9]+", " ", b.lower()).strip()


def why_not(username: str, data: dict, config: dict) -> Optional[str]:
    """Why a profile gets no card ("excluded", "not_member", "no_interests", "not_opted_in"), or None."""
    required, opt_in, exclude = listing_rules(config)
    if username.lower() in exclude:
        return "excluded"
    if commons.is_stemedplus_member(data) is False:
        return "not_member"
    all_interests = commons.interests(data)
    if not [i for i in all_interests if not same(i, opt_in)]:
        return "no_interests"
    if required and not any(same(i, opt_in) for i in all_interests):
        return "not_opted_in"
    return None


def to_card(username: str, data: dict, config: dict) -> Optional[dict]:
    """The card for one profile, or None when it should not be shown."""
    if why_not(username, data, config):
        return None
    _, opt_in, _ = listing_rules(config)
    all_interests = commons.interests(data)
    opted_in = any(same(i, opt_in) for i in all_interests)
    shown = [i for i in all_interests if not same(i, opt_in)]
    name = re.sub(r"\s+", " ", str(data.get("name") or "")).strip() or username
    photo = str(data.get("avatar") or "").strip()
    orcid = str(data.get("orcid") or "").strip()
    return {
        "username": username,
        "name": name,
        "institution": re.sub(r"\s+", " ", str(data.get("institutional_affiliation") or "")).strip(),
        "orcid": orcid if re.fullmatch(r"\d{4}-\d{4}-\d{4}-\d{3}[\dX]", orcid) else "",
        "photo": photo if PHOTO.match(photo) and "mystery" not in photo else "",
        "interests": shown,
        "opted_in": opted_in,
        "profile": commons.profile_url(username),
    }


def collect(usernames: Iterable[str], config: dict, read: Callable = commons.iter_profiles) -> Tuple[List[dict], dict]:
    names = list(usernames)
    cards, counts = [], {"members": len(names), "answered": 0, "missing": 0, "unavailable": 0}
    for username, status, data in read(names):
        if status == commons.OK:
            counts["answered"] += 1
            reason = why_not(username, data, config)
            if reason:
                counts[reason] = counts.get(reason, 0) + 1
            else:
                cards.append(to_card(username, data, config))
        else:
            counts[status] += 1
    cards.sort(key=lambda c: (c["name"].lower(), c["username"]))
    counts["listed"] = len(cards)
    return cards, counts


def load_data(path: Path = DATA) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"updated": None, "counts": {}, "people": []}


def refresh(path: Path = DATA, config: Optional[dict] = None, list_members: Callable = commons.directory_usernames,
            read: Callable = commons.iter_profiles, now: Optional[dt.datetime] = None,
            force: bool = False) -> Tuple[bool, str]:
    """Update the saved copy from Commons. Returns (changed, message)."""
    config = config or load_config()
    old = load_data(path)
    try:
        usernames = list_members()
    except RuntimeError as exc:
        return False, f"Kept the last good copy: {exc}."
    cards, counts = collect(usernames, config, read)
    if counts["answered"] < MIN_ANSWERED * max(1, counts["members"]):
        return False, (f"Kept the last good copy: only {counts['answered']} of {counts['members']} profiles answered.")
    if old["people"] and not force and len(cards) < MIN_KEPT * len(old["people"]):
        return False, (f"Kept the last good copy: this read found {len(cards)} cards, under half of the "
                       f"{len(old['people'])} saved. Check Commons, then run again with --force if this is right.")
    now = now or dt.datetime.now(dt.timezone.utc)
    new = {"updated": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "counts": counts, "people": cards}
    if new["people"] == old["people"] and new["counts"] == old.get("counts"):
        return False, f"No change: {counts['listed']} of {counts['members']} members listed."
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(new, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    skipped = ", ".join(f"{k.replace('_', ' ')}: {v}" for k, v in counts.items()
                        if k in ("no_interests", "not_member", "not_opted_in", "excluded"))
    return True, (f"Updated: {counts['listed']} of {counts['members']} members listed "
                  f"({counts['answered']} profiles read; not listed, {skipped or 'none'}).")
