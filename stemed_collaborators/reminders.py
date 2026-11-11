"""The yearly check, run once a day by .github/workflows/reminders.yml.

For each profile, counted from the day it was last confirmed:

    12 months   a private message on STEMEd+ Commons: reply KEEP to stay listed
    14 months   a last reminder
    15 months   the profile is removed, with a message saying they can rejoin any time

A reply containing the word KEEP (to either message) renews the profile for another year, as does the
"Keep my profile" GitHub form or sending the join form again.

Messages are sent and replies read through the STEMEd+ Commons (BuddyPress) REST API, signed in as the
account in the COMMONS_USER and COMMONS_APP_PASSWORD secrets (a WordPress application password). Without
them, nothing is sent: the job prints what it would do, and opens or updates a GitHub issue listing the
people to message by hand, with a link that starts each message.

    python -m stemed_collaborators.reminders [--dry-run] [--report report.md]
"""
import argparse
import base64
import datetime as dt
import html
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional

import yaml

from . import profiles

API = "https://stemedplus.org/wp-json/buddypress/v1"
SITE = "https://jlib271.github.io/stemed-collaborators/"
REPO = "https://github.com/JLib271/stemed-collaborators"
COMPOSE = "https://stemedplus.org/members/me/messages/compose/?r={username}"
KEEP = re.compile(r"\bkeep\b", re.I)


def _date(d: dt.date) -> str:
    return f"{d:%B} {d.day}, {d.year}"


def first_message(p: dict, removal: dt.date) -> Dict[str, str]:
    first = p["name"].split()[0]
    return {
        "subject": "Keep your STEMEd+ Collaborators profile?",
        "message": (
            f"Hi {first},\n\n"
            f"A year ago you listed yourself in STEMEd+ Collaborators ({SITE}), so people can find you for "
            "collaborations, mentoring, and writing partners.\n\n"
            "Would you like to stay listed? Just reply KEEP to this message. To change your answers, send the "
            f"join form again from {SITE}\n\n"
            f"If we don't hear from you, your profile will be removed on {_date(removal)}. "
            "You can rejoin any time.\n\nThank you,\nSTEMEd+ Commons"),
    }


def final_message(p: dict, removal: dt.date) -> Dict[str, str]:
    first = p["name"].split()[0]
    return {
        "subject": "Last reminder: your STEMEd+ Collaborators profile",
        "message": (
            f"Hi {first},\n\n"
            f"Your STEMEd+ Collaborators profile will be removed on {_date(removal)} unless you'd like to keep it. "
            "To stay listed, just reply KEEP to this message.\n\nThank you,\nSTEMEd+ Commons"),
    }


def removed_message(p: dict) -> Dict[str, str]:
    first = p["name"].split()[0]
    return {
        "subject": "Your STEMEd+ Collaborators profile was removed",
        "message": (
            f"Hi {first},\n\n"
            "We didn't hear from you, so your STEMEd+ Collaborators profile has been removed. "
            f"You're welcome back any time: use \"Join the directory\" at {SITE}\n\nThank you,\nSTEMEd+ Commons"),
    }


class Commons:
    """The few STEMEd+ Commons API calls the yearly check needs."""

    def __init__(self, user: str, app_password: str, api: str = API):
        token = base64.b64encode(f"{user}:{app_password}".encode()).decode()
        self.headers = {"Authorization": f"Basic {token}", "Accept": "application/json",
                        "User-Agent": "stemed-collaborators-reminders"}
        self.api = api
        self._ids: Dict[str, int] = {}

    def _call(self, method: str, path: str, params: dict = None, body: dict = None):
        url = self.api + path + ("?" + urllib.parse.urlencode(params, doseq=True) if params else "")
        data = json.dumps(body).encode() if body is not None else None
        headers = dict(self.headers, **({"Content-Type": "application/json"} if data else {}))
        req = urllib.request.Request(url, data=data, method=method, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode() or "null")

    def me(self) -> int:
        return int(self._call("GET", "/members/me")["id"])

    def user_id(self, username: str) -> Optional[int]:
        if username not in self._ids:
            found = None
            for m in self._call("GET", "/members", {"search": username, "per_page": 20}) or []:
                slug = (m.get("link") or "").rstrip("/").rsplit("/", 1)[-1]
                if username in (m.get("user_login"), m.get("mention_name"), slug):
                    found = int(m["id"])
                    break
            self._ids[username] = found
        return self._ids[username]

    def send(self, username: str, subject: str, message: str) -> bool:
        uid = self.user_id(username)
        if not uid:
            return False
        self._call("POST", "/messages", body={"recipients": [uid], "subject": subject, "message": message})
        return True

    def keep_replies(self, since: dt.date) -> Dict[int, dt.date]:
        """User id -> date of their latest message to this account, sent on or after `since`, that says KEEP."""
        me, out, page = self.me(), {}, 1
        while page <= 10:
            threads = self._call("GET", "/messages", {"box": "inbox", "per_page": 50, "page": page,
                                                     "user_id": me}) or []
            for t in threads:
                for m in t.get("messages") or []:
                    sender = int(m.get("sender_id") or 0)
                    sent = str(m.get("date_sent") or m.get("date") or "")[:10]
                    body = m.get("message") or {}
                    text = body.get("raw") or body.get("rendered") if isinstance(body, dict) else str(body)
                    text = html.unescape(re.sub(r"<[^>]+>", " ", text or ""))
                    if sender and sender != me and sent and KEEP.search(text):
                        when = dt.date.fromisoformat(sent)
                        if when >= since and when > out.get(sender, dt.date.min):
                            out[sender] = when
            if len(threads) < 50:
                break
            page += 1
        return out


def plan(entries, today: dt.date) -> List[dict]:
    """What is due for each profile: 'first', 'final', or 'remove'."""
    todo = []
    for slug, data in entries:
        confirmed, reminded = data["confirmed"], [d for d in (data.get("reminded") or []) if d > data["confirmed"]]
        age = (today - confirmed).days
        removal = confirmed + dt.timedelta(days=profiles.CONFIRM_DAYS)
        if age >= profiles.CONFIRM_DAYS:
            todo.append({"slug": slug, "data": data, "step": "remove", "removal": removal})
        elif age >= profiles.FINAL_DAYS and len(reminded) < 2:
            todo.append({"slug": slug, "data": data, "step": "final", "removal": removal})
        elif age >= profiles.REMIND_DAYS and not reminded:
            todo.append({"slug": slug, "data": data, "step": "first", "removal": removal})
    return todo


def _write(folder: Path, slug: str, data: dict) -> None:
    (folder / f"{slug}.yml").write_text(profiles.dump(data),
                                        encoding="utf-8")


def run(today: dt.date, commons: Optional[Commons], folder: Path = profiles.PROFILES) -> List[str]:
    """Do the day's work and return report lines (Markdown)."""
    entries, problems = profiles.load(folder)
    if problems:
        raise SystemExit("Problems in profiles/:\n  " + "\n  ".join(problems))
    lines = []

    # 1. KEEP replies renew a profile that has been reminded.
    if commons:
        reminded = [(s, d) for s, d in entries if d.get("reminded")]
        if reminded:
            earliest = min(min(d["reminded"]) for _, d in reminded)
            replies = commons.keep_replies(earliest)
            for slug, data in reminded:
                uid = commons.user_id(slug)
                when = replies.get(uid) if uid else None
                if when and when >= min(data["reminded"]):
                    data["confirmed"] = today
                    data.pop("reminded", None)
                    _write(folder, slug, data)
                    lines.append(f"- Renewed `{slug}`: replied KEEP on {when.isoformat()}.")
        entries, _ = profiles.load(folder)

    # 2. Reminders and removals that are due.
    for item in plan(entries, today):
        slug, data, step = item["slug"], item["data"], item["step"]
        msg = (removed_message(data) if step == "remove" else
               final_message(data, item["removal"]) if step == "final" else first_message(data, item["removal"]))
        sent = False
        if commons:
            try:
                sent = commons.send(slug, msg["subject"], msg["message"])
            except Exception as exc:  # keep going for everyone else
                lines.append(f"- Could not message `{slug}` ({type(exc).__name__}); will try again tomorrow.")
                continue
        if step == "remove":
            (folder / f"{slug}.yml").unlink()
            lines.append(f"- Removed `{slug}` ({data['name']}): not confirmed since {data['confirmed'].isoformat()}."
                         + ("" if sent else f" Let them know: [message on Commons]({COMPOSE.format(username=slug)})."))
        elif sent:
            data["reminded"] = list(data.get("reminded") or []) + [today]
            _write(folder, slug, data)
            lines.append(f"- Sent the {'last' if step == 'final' else 'first'} reminder to `{slug}` ({data['name']}).")
        else:
            why = "could not find them on Commons" if commons else "messages are not set up"
            lines.append(f"- Due: {'last' if step == 'final' else 'first'} reminder for `{slug}` ({data['name']}), "
                         f"{why}. [Message on STEMEd+ Commons]({COMPOSE.format(username=slug)}); when they reply, "
                         f"use the [Keep my profile]({REPO}/issues/new?template=keep_profile.yml) form for them.")
    return lines


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true", help="send nothing and change nothing; print the plan")
    ap.add_argument("--report", type=Path, help="write the report (Markdown) here")
    args = ap.parse_args(argv)
    today = dt.date.today()
    user, pw = os.environ.get("COMMONS_USER"), os.environ.get("COMMONS_APP_PASSWORD")
    if args.dry_run:
        entries, _ = profiles.load()
        lines = [f"- {i['step']}: `{i['slug']}`" for i in plan(entries, today)]
    else:
        lines = run(today, Commons(user, pw) if user and pw else None)
    text = "\n".join(lines) if lines else "Nothing due today."
    print(text)
    if args.report:
        args.report.write_text(text + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
