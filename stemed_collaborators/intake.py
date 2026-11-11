"""Turn an approved issue into a change to profiles/.

Run by .github/workflows/intake.yml when a maintainer adds the "approved" label. The issue
text is read from environment variables (never pasted into a shell command):

    ISSUE_BODY    the issue text
    ISSUE_LABELS  the issue's labels, as a JSON list

    python -m stemed_collaborators.intake --result result.md

Writes a short reply for the issue to --result, and "changed=true|false" and
"username=..." to $GITHUB_OUTPUT when that is set.
"""
import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path

import yaml

from . import forms, profiles


def handle(body: str, labels, today: dt.date, folder: Path = profiles.PROFILES):
    """Return (changed, username, reply)."""
    kind = forms.form_kind(body, labels)
    if kind == "remove":
        username = forms.username_from_issue(body)
        path = folder / f"{username}.yml"
        if not username or not profiles.USERNAME.match(username) or not path.exists():
            return False, username, f"No profile was found for `{username or '(blank)'}`, so nothing was removed."
        path.unlink()
        return True, username, (f"Removed the profile for `{username}`. It will leave the site at the next build "
                                "(within a few minutes).")
    if kind == "keep":
        username = forms.username_from_issue(body)
        path = folder / f"{username}.yml"
        if not username or not profiles.USERNAME.match(username) or not path.exists():
            return False, username, (f"No profile was found for `{username or '(blank)'}`. If it was removed, "
                                     "please send the join form again.")
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        data["confirmed"] = today
        data.pop("reminded", None)
        path.write_text(profiles.dump(data), encoding="utf-8")
        return True, username, (f"Thanks! The profile for `{username}` stays listed. We'll check in again around "
                                f"{(today + dt.timedelta(days=profiles.REMIND_DAYS)).isoformat()}.")
    if kind == "join":
        username = forms.username_from_issue(body)
        previous = None
        if username and profiles.USERNAME.match(username) and (folder / f"{username}.yml").exists():
            previous = yaml.safe_load((folder / f"{username}.yml").read_text(encoding="utf-8"))
        username, data, problems = forms.profile_from_issue(body, today, previous)
        if problems:
            return False, username, ("This form could not be listed yet. Please edit the issue to fix the following, "
                                     "and a maintainer will approve it again:\n\n" + "\n".join(f"- {p}" for p in problems))
        folder.mkdir(parents=True, exist_ok=True)
        text = profiles.dump(data)
        (folder / f"{username}.yml").write_text(text, encoding="utf-8")
        verb = "Updated" if previous else "Added"
        return True, username, (f"{verb} the profile for **{data['name']}** (`{username}`). It will appear on the site "
                                f"at the next build (within a few minutes). Then see who matches your profile: "
                                f"https://jlib271.github.io/stemed-collaborators/?me={username} (bookmark it). "
                                "Once a year we'll send a message on STEMEd+ Commons "
                                "asking whether to keep it; reply KEEP to stay listed.")
    return False, "", "This issue is not a join, update, keep, or remove form, so nothing was changed."


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--result", type=Path, required=True)
    args = ap.parse_args(argv)
    try:
        labels = [str(l) for l in json.loads(os.environ.get("ISSUE_LABELS") or "[]")]
    except ValueError:
        labels = []
    changed, username, reply = handle(os.environ.get("ISSUE_BODY", ""), labels, dt.date.today())
    args.result.write_text(reply + "\n", encoding="utf-8")
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as fh:
            fh.write(f"changed={'true' if changed else 'false'}\n")
            safe = username if profiles.USERNAME.match(username or "") else "unknown"
            fh.write(f"username={safe}\n")
    print(reply)
    return 0


if __name__ == "__main__":
    sys.exit(main())
