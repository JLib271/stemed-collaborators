"""Find Collaborators: build the page from STEMEd+ Commons profiles.

    python -m stemed_collaborators --refresh [--force]   read Commons, update data/collaborators.json
    python -m stemed_collaborators --out output           write the page from the saved copy

The page is one file, index.html, with the cards built in, so it also opens straight from a download.
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

from . import commons, directory

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ("stemedplus-commons-logo.png", "stemedplus-commons-logo-white.png", "stemedplus-theme.css",
          "manrope.woff", "manrope-OFL.txt")
MARK = "/*__DATA__*/null"


CONTACT = "https://stemedplus.org/contact-us/"


def load_organizations(path: Path = ROOT / "config" / "organizations.json") -> list:
    """Organization cards, checked: name, summary, and an https contact are required."""
    if not path.exists():
        return []
    out = []
    for i, o in enumerate(json.loads(path.read_text(encoding="utf-8")).get("organizations", [])):
        for key in ("name", "summary", "contact"):
            if not str(o.get(key, "")).strip():
                raise SystemExit(f"config/organizations.json, organization {i + 1}: {key} is required")
        for key in ("contact", "website"):
            if o.get(key) and not str(o[key]).startswith("https://"):
                raise SystemExit(f"config/organizations.json, {o['name']}: {key} must start with https://")
        logo = str(o.get("logo", "")).strip()
        if logo and not logo.startswith("https://") and not (ROOT / "site" / logo).exists():
            raise SystemExit(f"config/organizations.json, {o['name']}: logo {logo} is not in site/")
        out.append({"name": o["name"].strip(), "summary": o["summary"].strip(),
                    "looking_for": str(o.get("looking_for", "")).strip(), "logo": logo,
                    "interests": [str(x).strip() for x in o.get("interests", []) if str(x).strip()],
                    "website": str(o.get("website", "")).strip(), "contact": o["contact"].strip()})
    return out


def page_data(config: dict, data: dict) -> dict:
    required, opt_in, _ = directory.listing_rules(config)
    return {
        "updated": data.get("updated"),
        "counts": data.get("counts") or {},
        "preview": not required,  # true: everyone with interests is listed (the opt-in step is not shown)
        "opt_in_interest": opt_in,
        "edit_profile": commons.EDIT_PROFILE,
        "directory": commons.BASE + "/members/",
        "join_url": config.get("join_url", ""),
        "people": data.get("people") or [],
        "organizations": load_organizations(),
        "contact_url": CONTACT,
    }


def build(out: Path, config: dict = None, data: dict = None) -> dict:
    config = config or directory.load_config()
    data = data if data is not None else directory.load_data()
    payload = page_data(config, data)
    page = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
    if MARK not in page:
        raise SystemExit("site/index.html has lost its data marker " + MARK)
    blob = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(page.replace(MARK, blob), encoding="utf-8")
    for name in ASSETS:
        shutil.copyfile(ROOT / "site" / name, out / name)
    print(f"Wrote the page with {len(payload['people'])} people and {len(payload['organizations'])} organization card(s)"
          f"{'' if payload['preview'] else ' (opt-in required)'}.")
    return payload


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=Path("output"))
    ap.add_argument("--refresh", action="store_true", help="read Commons and update data/collaborators.json")
    ap.add_argument("--force", action="store_true", help="with --refresh: accept a large drop in cards")
    args = ap.parse_args(argv)
    if args.refresh:
        changed, message = directory.refresh(force=args.force)
        print(message)
        return 0
    build(args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
