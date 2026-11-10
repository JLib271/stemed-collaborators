"""The GitHub issue forms people use to join, update, or leave the directory, and the
reader that turns an approved form into a profile file.

    python -m stemed_collaborators.forms --write     # rewrite .github/ISSUE_TEMPLATE/ from config/vocab.json

The forms are generated from the shared vocabularies so the choices on the form and the
choices the site accepts can never drift apart (a test checks this).
"""
import argparse
import datetime as dt
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import yaml

from . import profiles
from .disciplines import DISCIPLINES

ROOT = profiles.ROOT
TEMPLATES = ROOT / ".github" / "ISSUE_TEMPLATE"
VOCAB = profiles.VOCAB

# Form field id -> label shown on the form. The reader finds answers by these labels.
LABELS: Dict[str, str] = {
    "name": "Your name as you want it shown",
    "username": "Your STEMEd+ Commons username",
    "commons_profile": "Link to your STEMEd+ Commons profile",
    "pronouns": "Pronouns (optional)",
    "career_stage": "Career stage",
    "institution": "Institution or organization (optional)",
    "institution_types": "Institution type (optional, choose any)",
    "disciplines": "Disciplines (choose at least one)",
    "methods": "Methods you work with (choose at least one)",
    "topics": "Topics you work on (optional)",
    "offers": "What you can offer others (choose at least one)",
    "seeking": "What you are looking for (optional)",
    "about": "A few sentences about your work",
    "orcid": "ORCID iD (optional)",
    "consent": "Consent",
}
CONSENT = [
    "I am the person described in this form.",
    "I agree that everything in this form will be shown publicly on STEMEd+ Collaborators and kept in its GitHub repository.",
    "I understand a maintainer will message me on STEMEd+ Commons to confirm before I am listed, and that I can ask to be removed at any time.",
]
NONE = "_No response_"
REMOVE_NOTE = "Anything we should know? (optional)"


def _checkboxes(fid: str, options: List[str], required: bool = False) -> dict:
    item = {"type": "checkboxes", "id": fid,
            "attributes": {"label": LABELS[fid], "options": [{"label": o} for o in options]}}
    if required:
        item["attributes"]["options"] = [{"label": o, "required": True} for o in options]
    return item


def _input(fid: str, required: bool, **attrs) -> dict:
    item = {"type": "input", "id": fid, "attributes": {"label": LABELS[fid], **attrs}}
    if required:
        item["validations"] = {"required": True}
    return item


def join_form() -> dict:
    return {
        "name": "Join or update the directory",
        "description": "List yourself in STEMEd+ Collaborators so people can find you and message you on STEMEd+ Commons.",
        "title": "Join: ",
        "labels": ["directory: join"],
        "body": [
            {"type": "markdown", "attributes": {"value": (
                "Thanks for joining! Everything you enter here is **public**. Your email address is never shown: "
                "people contact you through STEMEd+ Commons.\n\n"
                "You need a free STEMEd+ Commons account first. Before you are listed, a maintainer sends you a "
                "private message on STEMEd+ Commons to confirm it is really you.\n\n"
                "**Updating your profile?** Fill in the whole form again; the new answers replace the old ones. "
                "Profiles are shown for one year after they are last confirmed, so send this form once a year to stay listed.")}},
            _input("name", True, placeholder="e.g. Maria Lopez"),
            _input("username", True, description="The name after /members/ in your profile link, e.g. libarkin in stemedplus.profile.hcommons.org/members/libarkin/",
                   placeholder="e.g. mlopez"),
            _input("commons_profile", True, placeholder="https://stemedplus.profile.hcommons.org/members/yourname/"),
            _input("pronouns", False, placeholder="e.g. she/her"),
            {"type": "dropdown", "id": "career_stage",
             "attributes": {"label": LABELS["career_stage"], "options": VOCAB["career_stages"]},
             "validations": {"required": True}},
            _input("institution", False, placeholder="e.g. University of Texas Rio Grande Valley"),
            _checkboxes("institution_types", VOCAB["institution_types"]),
            _checkboxes("disciplines", list(DISCIPLINES)),
            _checkboxes("methods", VOCAB["methods"]),
            _input("topics", False, description="Separate topics with commas.",
                   placeholder="e.g. sense of belonging, organic chemistry labs, teaching assistants"),
            {"type": "markdown", "attributes": {"value": (
                "**What you can offer and what you are looking for** use the same list, so people can find "
                "two-way matches. Please fill in both. If you only want to offer help right now, leave "
                "\"What you are looking for\" blank.")}},
            _checkboxes("offers", VOCAB["collaboration"]),
            _checkboxes("seeking", VOCAB["collaboration"]),
            {"type": "textarea", "id": "about",
             "attributes": {"label": LABELS["about"],
                            "description": f"Up to {profiles.ABOUT_MAX} characters. What you study, and what kind of collaboration you want.",
                            "placeholder": "I study how first-generation students ..."},
             "validations": {"required": True}},
            _input("orcid", False, placeholder="0000-0002-1825-0097"),
            _checkboxes("consent", CONSENT, required=True),
        ],
    }


def remove_form() -> dict:
    return {
        "name": "Remove my profile",
        "description": "Take your profile out of STEMEd+ Collaborators.",
        "title": "Remove: ",
        "labels": ["directory: remove"],
        "body": [
            {"type": "markdown", "attributes": {"value": (
                "We will remove your profile from the site and from the repository. A maintainer may message you "
                "on STEMEd+ Commons to confirm. Earlier versions stay in the repository's history; ask in this "
                "issue if you need those removed too.")}},
            _input("username", True, placeholder="e.g. mlopez"),
            {"type": "textarea", "id": "why", "attributes": {"label": REMOVE_NOTE}},
        ],
    }


def report_form() -> dict:
    return {
        "name": "Report a problem with a profile",
        "description": "A profile is wrong, out of date, or was not made by the person it describes.",
        "title": "Problem with profile: ",
        "labels": ["directory: report"],
        "body": [
            {"type": "input", "id": "username", "attributes": {"label": "Username of the profile"},
             "validations": {"required": True}},
            {"type": "textarea", "id": "problem", "attributes": {"label": "What is wrong?"},
             "validations": {"required": True}},
        ],
    }


def config_form() -> dict:
    return {
        "blank_issues_enabled": True,
        "contact_links": [{
            "name": "No GitHub account? Email the maintainer",
            "url": "https://github.com/JLib271/stemed-collaborators#join-without-a-github-account",
            "about": "The README gives the maintainer's email address. We will add you and confirm on STEMEd+ Commons.",
        }],
    }


def render_forms() -> Dict[str, str]:
    def dump(d):
        return yaml.safe_dump(d, sort_keys=False, allow_unicode=True, width=120)
    return {
        "join_directory.yml": dump(join_form()),
        "remove_profile.yml": dump(remove_form()),
        "report_profile.yml": dump(report_form()),
        "config.yml": dump(config_form()),
    }


# ---------- reading a submitted form ----------

def sections(body: str) -> Dict[str, str]:
    """GitHub renders an issue form as '### Label' headings, each followed by the answer."""
    out, label, buf = {}, None, []
    for line in (body or "").replace("\r\n", "\n").split("\n"):
        m = re.match(r"^###\s+(.*?)\s*$", line)
        if m:
            if label is not None:
                out[label] = "\n".join(buf).strip()
            label, buf = m.group(1), []
        elif label is not None:
            buf.append(line)
    if label is not None:
        out[label] = "\n".join(buf).strip()
    return out


def _text(v: str) -> str:
    v = (v or "").strip()
    return "" if v == NONE else v


def _ticked(v: str) -> List[str]:
    return [m.group(1).strip() for m in re.finditer(r"^- \[[xX]\]\s+(.*)$", v or "", re.M)]


def profile_from_issue(body: str, today: dt.date, previous: dict = None) -> Tuple[str, dict, List[str]]:
    """Return (username, profile data, problems) for a join/update form."""
    s = sections(body)
    get = lambda key: _text(s.get(LABELS[key], ""))  # noqa: E731
    problems = []
    if len(_ticked(s.get(LABELS["consent"], ""))) != len(CONSENT):
        problems.append("All three consent boxes must be ticked.")
    username = get("username").lstrip("@").strip()
    data = {
        "name": get("name"),
        "username": username,
        "commons_profile": get("commons_profile"),
        "career_stage": get("career_stage"),
        "disciplines": _ticked(s.get(LABELS["disciplines"], "")),
        "methods": _ticked(s.get(LABELS["methods"], "")),
        "offers": _ticked(s.get(LABELS["offers"], "")),
        "about": " ".join(get("about").split()),
        "listed": (previous or {}).get("listed") or today,
        "confirmed": today,
    }
    for key in ("pronouns", "institution", "orcid"):
        if get(key):
            data[key] = get(key)
    seeking = _ticked(s.get(LABELS["seeking"], ""))
    if seeking:
        data["seeking"] = seeking
    types = _ticked(s.get(LABELS["institution_types"], ""))
    if types:
        data["institution_types"] = types
    topics = [t.strip() for t in get("topics").split(",") if t.strip()]
    if topics:
        data["topics"] = topics
    if data.get("orcid"):
        data["orcid"] = re.sub(r"^https?://orcid\.org/", "", data["orcid"])
    problems += [p.split(": ", 1)[1] if ": " in p else p for p in profiles.check(data, username or "?")]
    return username, data, problems


def form_kind(body: str, labels) -> str:
    """'join', 'remove', or '' for a submitted issue. Uses the label the form adds, and falls back
    to the form's own questions in case the label does not exist in the repository."""
    if "directory: remove" in labels:
        return "remove"
    if "directory: join" in labels:
        return "join"
    s = sections(body)
    if LABELS["consent"] in s:
        return "join"
    if REMOVE_NOTE in s and LABELS["username"] in s:
        return "remove"
    return ""


def username_from_issue(body: str) -> str:
    return _text(sections(body).get(LABELS["username"], "")).lstrip("@").strip()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--write", action="store_true", help="rewrite the issue forms")
    args = ap.parse_args(argv)
    if args.write:
        TEMPLATES.mkdir(parents=True, exist_ok=True)
        for name, text in render_forms().items():
            (TEMPLATES / name).write_text("# Generated by: python -m stemed_collaborators.forms --write\n" + text,
                                          encoding="utf-8")
        print(f"Wrote {len(render_forms())} files to {TEMPLATES}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
