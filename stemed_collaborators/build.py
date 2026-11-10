"""Read the collaborator profiles and write the directory site.

    python -m stemed_collaborators --out output
    python -m stemed_collaborators --validate      # only check profiles/*.yml

Output (all static, served by GitHub Pages):
    index.html              search and matching page
    collaborators.json      the active profiles and the shared vocabularies
"""
import argparse
import datetime as dt
import json
import shutil
import sys
from pathlib import Path
from typing import Optional

from . import profiles
from .disciplines import DISCIPLINES

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ("stemedplus-commons-logo.png", "stemedplus-commons-logo-white.png", "stemedplus-theme.css",
          "manrope.woff", "manrope-OFL.txt")


def load_config(name: str) -> dict:
    return json.loads((ROOT / "config" / name).read_text(encoding="utf-8"))


def run(out: Path, today: dt.date, now: Optional[dt.datetime] = None, folder: Path = profiles.PROFILES) -> dict:
    now = now or dt.datetime.combine(today, dt.time(12), tzinfo=dt.timezone.utc)
    site = load_config("site.json")
    entries, problems = profiles.load(folder)
    if problems:
        raise SystemExit("Problems in profiles/:\n  " + "\n  ".join(problems))
    records = [profiles.to_record(slug, data, today) for slug, data in entries]
    active = [r for r in records if r["active"]]
    active.sort(key=lambda r: r["name"].lower())
    payload = {
        "generated": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "today": today.isoformat(),
        "site": site,
        "disciplines": list(DISCIPLINES),
        "vocab": profiles.VOCAB,
        # Only a count of lapsed profiles is published, never who they are.
        "lapsed": len(records) - len(active),
        "people": active,
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / "collaborators.json").write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n",
                                            encoding="utf-8")
    shutil.copyfile(ROOT / "site" / "index.html", out / "index.html")
    for name in ASSETS:
        shutil.copyfile(ROOT / "site" / name, out / name)
    print(f"Wrote {len(active)} active profile(s); {payload['lapsed']} waiting for the person to confirm again.")
    return payload


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=Path("output"))
    ap.add_argument("--validate", action="store_true", help="only check profiles/*.yml")
    args = ap.parse_args(argv)
    if args.validate:
        entries, problems = profiles.load()
        for p in problems:
            print(p)
        print(f"{len(entries)} valid profile(s), {len(problems)} problem(s).")
        return 1 if problems else 0
    run(args.out, dt.date.today())
    return 0


if __name__ == "__main__":
    sys.exit(main())
