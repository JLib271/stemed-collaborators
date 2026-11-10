"""Load and check the opt-in collaborator profiles in profiles/*.yml.

Every profile is a person who asked to be listed (through the "Join the directory" form)
and was approved by a maintainer. A profile that has not been confirmed for
CONFIRM_DAYS is left off the site until the person confirms it again.
"""
import datetime as dt
import json
import re
from pathlib import Path
from typing import List, Tuple

import yaml

from .disciplines import DISCIPLINES

ROOT = Path(__file__).resolve().parent.parent
PROFILES = ROOT / "profiles"
VOCAB = json.loads((ROOT / "config" / "vocab.json").read_text(encoding="utf-8"))
CONFIRM_DAYS = 365
REMIND_DAYS = 30          # flag profiles this close to expiring
ABOUT_MAX = 400
USERNAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,59}$")
COMMONS_HOSTS = ("hcommons.org", "stemedplus.org")
ORCID = re.compile(r"^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$")

REQUIRED = ("name", "username", "commons_profile", "career_stage", "disciplines", "methods",
            "offers", "about", "confirmed")
LISTS = {
    "disciplines": list(DISCIPLINES),
    "methods": VOCAB["methods"],
    "offers": VOCAB["collaboration"],
    "seeking": VOCAB["collaboration"],
    "institution_types": VOCAB["institution_types"],
}
OPTIONAL = ("pronouns", "institution", "institution_types", "topics", "orcid", "listed", "seeking")


def is_commons_url(url: str) -> bool:
    m = re.match(r"^https://([^/]+)(/.*)?$", url or "")
    return bool(m) and any(m.group(1) == h or m.group(1).endswith("." + h) for h in COMMONS_HOSTS)


def check(data: dict, slug: str) -> List[str]:
    """Problems with one profile, as readable sentences (empty if it is fine)."""
    out = []
    if not isinstance(data, dict):
        return [f"{slug}: not a YAML mapping"]
    for key in REQUIRED:
        if data.get(key) in (None, "", []):
            out.append(f"{slug}: missing {key}")
    for key in data:
        if key not in REQUIRED and key not in OPTIONAL:
            out.append(f"{slug}: unknown field {key!r}")
    if data.get("username") and data["username"] != slug:
        out.append(f"{slug}: username {data['username']!r} must match the file name")
    if data.get("username") and not USERNAME.match(str(data["username"])):
        out.append(f"{slug}: username has characters that are not allowed")
    if data.get("commons_profile") and not is_commons_url(data["commons_profile"]):
        out.append(f"{slug}: commons_profile must be an https link on hcommons.org or stemedplus.org")
    if data.get("career_stage") and data["career_stage"] not in VOCAB["career_stages"]:
        out.append(f"{slug}: unknown career_stage {data['career_stage']!r}")
    for key, allowed in LISTS.items():
        val = data.get(key)
        if val is None:
            continue
        if not isinstance(val, list):
            out.append(f"{slug}: {key} must be a list")
            continue
        for v in val:
            if v not in allowed:
                out.append(f"{slug}: unknown {key} value {v!r}")
    if data.get("topics") is not None and (not isinstance(data["topics"], list)
                                           or not all(isinstance(t, str) and t.strip() for t in data["topics"])):
        out.append(f"{slug}: topics must be a list of words or phrases")
    if isinstance(data.get("about"), str) and len(data["about"]) > ABOUT_MAX:
        out.append(f"{slug}: about is longer than {ABOUT_MAX} characters")
    if data.get("orcid") and not ORCID.match(str(data["orcid"])):
        out.append(f"{slug}: orcid should look like 0000-0002-1825-0097")
    for key in ("confirmed", "listed"):
        if data.get(key) is not None and not isinstance(data[key], dt.date):
            out.append(f"{slug}: {key} must be a date (YYYY-MM-DD)")
    return out


def load(folder: Path = PROFILES) -> Tuple[List[Tuple[str, dict]], List[str]]:
    entries, problems = [], []
    for path in sorted(folder.glob("*.yml")):
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            problems.append(f"{path.stem}: not valid YAML ({exc})")
            continue
        p = check(data, path.stem)
        if p:
            problems += p
        else:
            entries.append((path.stem, data))
    return entries, problems


def to_record(slug: str, data: dict, today: dt.date) -> dict:
    confirmed: dt.date = data["confirmed"]
    expires = confirmed + dt.timedelta(days=CONFIRM_DAYS)
    return {
        "id": slug,
        "file": f"profiles/{slug}.yml",
        "name": data["name"].strip(),
        "pronouns": (data.get("pronouns") or "").strip(),
        "commons_profile": data["commons_profile"],
        "career_stage": data["career_stage"],
        "institution": (data.get("institution") or "").strip(),
        "institution_types": data.get("institution_types") or [],
        "disciplines": data["disciplines"],
        "methods": data["methods"],
        "topics": [t.strip() for t in (data.get("topics") or [])],
        "offers": data["offers"],
        "seeking": data.get("seeking") or [],
        "about": data["about"].strip(),
        "orcid": data.get("orcid") or "",
        "listed": (data.get("listed") or confirmed).isoformat(),
        "confirmed": confirmed.isoformat(),
        "expires": expires.isoformat(),
        "active": today <= expires,
        "expiring_soon": today <= expires <= today + dt.timedelta(days=REMIND_DAYS),
    }
