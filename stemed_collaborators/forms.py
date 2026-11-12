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

from . import commons, profiles
from .disciplines import DISCIPLINES

ROOT = profiles.ROOT
TEMPLATES = ROOT / ".github" / "ISSUE_TEMPLATE"
VOCAB = profiles.VOCAB

# Form field id -> label shown on the form. The reader finds answers by these labels.
LABELS: Dict[str, str] = {
    "name": "Your name as you want it shown (optional)",
    "username": "Your STEMEd+ Commons username",
    "commons_profile": "Link to your STEMEd+ Commons profile",
    "pronouns": "Pronouns (optional)",
    "career_stage": "Career stage",
    "institution": "Institution or organization (optional)",
    "institution_types": "Institution type (optional, choose any)",
    "disciplines": "Disciplines (choose at least one)",
    "methods": "Methods and expertise (choose at least one)",
    "topics": "Topics you work on (optional)",
    "offers": "What you can offer others (choose at least one)",
    "seeking": "What you are looking for (optional)",
    "about": "A few sentences about your work",
    "orcid": "ORCID iD (optional)",
    "consent": "Consent",
}
CONSENT = [
    "I am the person described in this form.",
    "I agree that everything in this form, and my name, institution, ORCID iD, and photo from my STEMEd+ Commons profile, will be shown publicly on STEMEd+ Collaborators and kept in its GitHub repository.",
    "I understand a maintainer will message me on STEMEd+ Commons to confirm before I am listed, and that I can ask to be removed at any time.",
]
NONE = "_No response_"
PASTE_LABEL = "The form email, pasted whole"
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
        "description": "Researchers, teachers, instructors, and informal educators: list yourself so people can find you and message you on STEMEd+ Commons.",
        "title": "Join: ",
        "labels": ["directory: join"],
        "body": [
            {"type": "markdown", "attributes": {"value": (
                "Thanks for joining! Everything you enter here is **public**. Your email address is never shown: "
                "people contact you through STEMEd+ Commons.\n\n"
                "You need a free STEMEd+ Commons account first. Your name, institution, ORCID iD, and photo are taken "
                "from your Commons profile unless you fill them in here. Before you are listed, a maintainer sends "
                "you a private message on STEMEd+ Commons to confirm it is really you.\n\n"
                "**Updating your profile?** Fill in the whole form again; the new answers replace the old ones. "
                "Profiles are shown for one year after they are last confirmed, so send this form once a year to stay listed.")}},
            _input("username", True, description="The name after /members/ in your profile link, e.g. libarkin in stemedplus.profile.hcommons.org/members/libarkin/. No STEMEd+ Commons account yet? Join first, free: https://stemedplus.org/join-stemed/",
                   placeholder="e.g. mlopez"),
            _input("name", False, description="Leave blank to use the name on your STEMEd+ Commons profile.",
                   placeholder="e.g. Maria Lopez"),
            _input("pronouns", False, placeholder="e.g. she/her"),
            {"type": "dropdown", "id": "career_stage",
             "attributes": {"label": LABELS["career_stage"], "options": VOCAB["career_stages"]},
             "validations": {"required": True}},
            _input("institution", False, description="Leave blank to use the one on your STEMEd+ Commons profile. If you fill it in, use the full name, not an abbreviation, so people can find you from STEMEd+ Graduate Programs.", placeholder="e.g. University of Texas Rio Grande Valley"),
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
                            "description": f"Up to {profiles.ABOUT_MAX} characters. What you study, teach, or lead, and what kind of collaboration you want.",
                            "placeholder": "I study how first-generation students ..."},
             "validations": {"required": True}},
            _input("orcid", False, description="Leave blank to use the one on your STEMEd+ Commons profile, if any.",
                   placeholder="0000-0002-1825-0097"),
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


KEEP_NOTE = "Anything else? (optional)"


def keep_form() -> dict:
    return {
        "name": "Keep my profile",
        "description": "Stay listed in STEMEd+ Collaborators for another year, with no changes.",
        "title": "Keep: ",
        "labels": ["directory: keep"],
        "body": [
            {"type": "markdown", "attributes": {"value": (
                "Profiles are checked once a year. Send this to stay listed for another year with no changes. "
                "(You can also just reply KEEP to the reminder message on STEMEd+ Commons.) To change your "
                "answers, send the join form again instead.")}},
            _input("username", True, placeholder="e.g. mlopez"),
            {"type": "textarea", "id": "note", "attributes": {"label": KEEP_NOTE}},
        ],
    }


def paste_form() -> dict:
    return {
        "name": "Add someone from the STEMEd+ form (maintainers)",
        "description": "Paste the email from the stemedplus.org Collaborators form to list someone who has no GitHub account.",
        "title": "Join (STEMEd+ form): ",
        "labels": ["directory: join"],
        "body": [
            {"type": "markdown", "attributes": {"value": (
                "For maintainers. Paste the whole notification email from the stemedplus.org form below, "
                "add the person's name to the title, and submit. Confirm with them on STEMEd+ Commons, then add "
                "the **approved** label, as for any join form. Their answers are read by the form's field names, "
                "so the stemedplus.org form must use the field names in `docs/stemedplus-form.md`.")}},
            {"type": "textarea", "id": "paste", "attributes": {"label": PASTE_LABEL, "render": "text"},
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
        "add_from_stemedplus_form.yml": dump(paste_form()),
        "keep_profile.yml": dump(keep_form()),
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


def _unfence(v: str) -> str:
    """GitHub shows a "render: text" answer inside a ``` code block; take the text out of it."""
    v = _text(v)
    m = re.match(r"^```[^\n]*\n(.*?)\n?```\s*$", v, re.S)
    return m.group(1) if m else v


def _text(v: str) -> str:
    v = (v or "").strip()
    return "" if v == NONE else v


def _ticked(v: str) -> List[str]:
    return [m.group(1).strip() for m in re.finditer(r"^- \[[xX]\]\s+(.*)$", v or "", re.M)]


def _norm_label(text: str) -> str:
    text = re.sub(r"\([^)]*\)", "", text or "")
    text = re.sub(r"[*:]+\s*$", "", text.strip())
    return " ".join(text.lower().split())


_LABEL_KEYS = {_norm_label(v): k for k, v in LABELS.items()}
# Short names a website form might use instead of the full question.
_LABEL_KEYS.update({"name": "name", "username": "username", "commons username": "username",
                    "commons profile": "commons_profile", "profile link": "commons_profile",
                    "pronouns": "pronouns", "institution": "institution", "institution type": "institution_types",
                    "disciplines": "disciplines", "methods": "methods", "methods and expertise": "methods", "methods you work with": "methods", "expertise": "methods", "topics": "topics",
                    "what i can offer": "offers", "can offer": "offers", "what i am looking for": "seeking",
                    "looking for": "seeking", "about": "about", "about your work": "about", "orcid": "orcid",
                    "orcid id": "orcid", "consent": "consent"})


def plain_sections(text: str) -> Dict[str, str]:
    """Answers from a pasted website-form email, by form field (key). A field starts at a line that is
    one of the form's labels, alone ("Career stage") or followed by its answer ("Career stage: Postdoc").
    Labels may drop their "(optional)" part, and may end with ":" or "*"."""
    out, key, buf = {}, None, []
    for line in (text or "").replace("\r\n", "\n").split("\n"):
        found, rest = _LABEL_KEYS.get(_norm_label(line)), ""
        if not found and ":" in line:
            left, right = line.split(":", 1)
            found, rest = _LABEL_KEYS.get(_norm_label(left)), right
        if found:
            if key:
                out[key] = "\n".join(buf).strip()
            key, buf = found, [rest.strip()] if rest.strip() else []
        elif key:
            buf.append(line)
    if key:
        out[key] = "\n".join(buf).strip()
    return out


def _chosen(text: str, options: List[str]) -> List[str]:
    """Options named in a free-text answer, however they are separated (commas, lines, bullets)."""
    hay = " ".join((text or "").lower().split())
    found = []
    for o in sorted(options, key=len, reverse=True):
        needle = " ".join(o.lower().split())
        if needle in hay:
            found.append(o)
            hay = hay.replace(needle, " | ")
    return [o for o in options if o in found]


def _build(get, multi, consent_ok: bool, today: dt.date, previous: dict = None,
           lookup=None) -> Tuple[str, dict, List[str]]:
    problems = [] if consent_ok else ["All three consent boxes must be ticked."]
    username = get("username").lstrip("@").strip()
    m = re.search(r"/members/([^/?#\s]+)", username)   # someone pasted their whole profile link
    if m:
        username = m.group(1)
    stage = get("career_stage")
    if stage not in VOCAB["career_stages"]:
        picked = _chosen(stage, VOCAB["career_stages"])
        stage = picked[0] if len(picked) == 1 else stage
    data = {
        "name": get("name"),
        "username": username,
        "commons_profile": get("commons_profile") or (commons.profile_url(username) if username else ""),
        "career_stage": stage,
        "disciplines": multi("disciplines", list(DISCIPLINES)),
        "methods": multi("methods", VOCAB["methods"]),
        "offers": multi("offers", VOCAB["collaboration"]),
        "about": " ".join(get("about").split()),
        "listed": (previous or {}).get("listed") or today,
        "confirmed": today,
    }
    for key in ("pronouns", "institution", "orcid"):
        if get(key):
            data[key] = get(key)
    seeking = multi("seeking", VOCAB["collaboration"])
    if seeking:
        data["seeking"] = seeking
    types = multi("institution_types", VOCAB["institution_types"])
    if types:
        data["institution_types"] = types
    topics = [t.strip() for t in re.split(r"[,\n]", get("topics")) if t.strip()]
    if topics:
        data["topics"] = topics
    problems += _from_commons(data, username, lookup)
    if data.get("orcid"):
        data["orcid"] = re.sub(r"^https?://orcid\.org/", "", data["orcid"])
    problems += [p.split(": ", 1)[1] if ": " in p else p for p in profiles.check(data, username or "?")]
    return username, data, problems


def _from_commons(data: dict, username: str, lookup) -> List[str]:
    """Fill what the form left blank from the member's public STEMEd+ Commons profile, and check that
    they belong to STEMEd+. `lookup` is commons.fetch (None: skip, as in most tests)."""
    if not lookup or not username or not profiles.USERNAME.match(username):
        return []
    status, info = lookup(username)
    if status == commons.MISSING:
        return [f"No STEMEd+ Commons account has the username `{username}`. It is the part after /members/ "
                "in your Commons profile link."]
    if status != commons.OK:
        return []          # Commons did not answer: use the form's own answers
    if commons.is_stemedplus_member(info) is False:
        return ["This Commons account has not joined STEMEd+ yet. Join at https://stemedplus.org/join-stemed/ "
                "and then send the form again."]
    if not data.get("name") and (info.get("name") or "").strip():
        data["name"] = info["name"].strip()
    if not data.get("institution") and (info.get("institutional_affiliation") or "").strip():
        data["institution"] = info["institutional_affiliation"].strip()
    if not data.get("orcid") and (info.get("orcid") or "").strip():
        data["orcid"] = info["orcid"].strip()
    photo = (info.get("avatar") or "").strip()
    if profiles.is_photo_url(photo):
        data["photo"] = photo
    return []


def profile_from_issue(body: str, today: dt.date, previous: dict = None,
                       lookup=None) -> Tuple[str, dict, List[str]]:
    """Return (username, profile data, problems) for a join/update form, or for a pasted
    stemedplus.org form email (the "Add someone from the STEMEd+ form" template)."""
    s = sections(body)
    if PASTE_LABEL in s:
        return profile_from_paste(_unfence(s[PASTE_LABEL]), today, previous, lookup)
    get = lambda key: _text(s.get(LABELS[key], ""))  # noqa: E731
    multi = lambda key, _opts: _ticked(s.get(LABELS[key], ""))  # noqa: E731
    consent_ok = len(_ticked(s.get(LABELS["consent"], ""))) == len(CONSENT)
    return _build(get, multi, consent_ok, today, previous, lookup)


def profile_from_paste(text: str, today: dt.date, previous: dict = None,
                       lookup=None) -> Tuple[str, dict, List[str]]:
    """Return (username, profile data, problems) for a pasted stemedplus.org form email."""
    s = plain_sections(text)
    get = lambda key: _text(s.get(key, ""))  # noqa: E731
    multi = lambda key, opts: _chosen(s.get(key, ""), opts)  # noqa: E731
    consent = " ".join(s.get("consent", "").lower().split())
    consent_ok = all(" ".join(c.lower().split())[:60] in consent for c in CONSENT)
    return _build(get, multi, consent_ok, today, previous, lookup)


def form_kind(body: str, labels) -> str:
    """'join', 'remove', or '' for a submitted issue. Uses the label the form adds, and falls back
    to the form's own questions in case the label does not exist in the repository."""
    if "directory: remove" in labels:
        return "remove"
    if "directory: join" in labels:
        return "join"
    if "directory: keep" in labels:
        return "keep"
    s = sections(body)
    if LABELS["consent"] in s or PASTE_LABEL in s:
        return "join"
    if REMOVE_NOTE in s and LABELS["username"] in s:
        return "remove"
    if KEEP_NOTE in s and LABELS["username"] in s:
        return "keep"
    return ""


def username_from_issue(body: str) -> str:
    s = sections(body)
    if PASTE_LABEL in s:
        return _text(plain_sections(_unfence(s[PASTE_LABEL])).get("username", "")).lstrip("@").strip()
    return _text(s.get(LABELS["username"], "")).lstrip("@").strip()


def website_form_spec() -> str:
    """The fields to build on stemedplus.org, in order, with their exact names and choices."""
    out = [
        "# STEMEd+ Collaborators: the website form",
        "",
        "Generated by `python -m stemed_collaborators.forms --write` from `config/vocab.json`. Do not edit by hand.",
        "",
        "Build these fields on the stemedplus.org form, in this order, with **exactly** these field names and",
        "choices, so a pasted notification email can be read automatically. Set the form to email each",
        "submission to the maintainer, with every field and its name in the email (most form tools do this by",
        "default, often called \"all fields\"). Then paste that email into the GitHub template",
        "\"Add someone from the STEMEd+ form (maintainers)\" and approve it as usual.",
        "",
        "Field names may leave out the part in brackets, such as \"(optional)\". Choices must keep their exact",
        "wording, but can be separated any way in the email (commas, new lines, or bullets).",
        "",
    ]
    n = [0]

    def add(key, kind, required, note="", options=None):
        n[0] += 1
        out.append(f"## {n[0]}. {LABELS[key]}")
        out.append("")
        out.append(f"- Type: {kind}")
        out.append(f"- Required: {'yes' if required else 'no'}")
        if note:
            out.append(f"- Help text: {note}")
        if options:
            out.append("- Choices:")
            out.extend(f"    - {o}" for o in options)
        out.append("")
    add("username", "single line of text", True, "The name after /members/ in your profile link, e.g. libarkin in stemedplus.profile.hcommons.org/members/libarkin/. No STEMEd+ Commons account yet? Join first, free: https://stemedplus.org/join-stemed/")
    add("name", "single line of text", False, "Leave blank to use the name on your STEMEd+ Commons profile.")
    add("pronouns", "single line of text", False)
    add("career_stage", "dropdown or radio buttons (choose one)", True, options=VOCAB["career_stages"])
    add("institution", "single line of text", False, "Leave blank to use the one on your STEMEd+ Commons profile. If you fill it in, use the full name, not an abbreviation (Michigan State University, not MSU), so people can find you from STEMEd+ Graduate Programs.")
    add("institution_types", "checkboxes (choose any)", False, options=VOCAB["institution_types"])
    add("disciplines", "checkboxes (at least one)", True, options=list(DISCIPLINES))
    add("methods", "checkboxes (at least one)", True, options=VOCAB["methods"])
    add("topics", "single line of text", False, "Separate topics with commas.")
    add("offers", "checkboxes (at least one)", True, "Same list as the next question. Please fill in both.", VOCAB["collaboration"])
    add("seeking", "checkboxes (choose any)", False, "Leave blank if you only want to offer help right now.", VOCAB["collaboration"])
    add("about", f"paragraph text, up to {profiles.ABOUT_MAX} characters", True, "What you study, teach, or lead, and what kind of collaboration you want.")
    add("orcid", "single line of text", False, "Leave blank to use the one on your STEMEd+ Commons profile, if any. e.g. 0000-0002-1825-0097")
    add("consent", "checkboxes (all three required)", True, options=CONSENT)
    out.append("Above the form, say: you need a free STEMEd+ Commons account first; your name, institution, ORCID iD,")
    out.append("and photo are taken from your Commons profile unless you fill them in here; everything is public; your")
    out.append("email address is never shown; a maintainer will message you on STEMEd+ Commons to confirm before you")
    out.append("are listed.")
    return "\n".join(out) + "\n"


SPEC = ROOT / "docs" / "stemedplus-form.md"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--write", action="store_true", help="rewrite the issue forms")
    args = ap.parse_args(argv)
    if args.write:
        TEMPLATES.mkdir(parents=True, exist_ok=True)
        for name, text in render_forms().items():
            (TEMPLATES / name).write_text("# Generated by: python -m stemed_collaborators.forms --write\n" + text,
                                          encoding="utf-8")
        SPEC.parent.mkdir(parents=True, exist_ok=True)
        SPEC.write_text(website_form_spec(), encoding="utf-8")
        print(f"Wrote {len(render_forms())} files to {TEMPLATES} and {SPEC}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
