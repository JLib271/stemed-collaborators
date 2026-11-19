import json
import tempfile
import unittest
from pathlib import Path

from stemed_collaborators import build, commons, directory

PAGE1 = """<div class="member-grid">
<div class="member-card"><p class="name"><a href="/members/ana/" class="member-card-link">Ana</a></p></div>
<div class="member-card"><p class="name"><a href="https://stemedplus.profile.hcommons.org/members/ben.k/" class="member-card-link">Ben</a></p></div>
<div class="member-card"><p class="name"><a href="/members/cy/" class="member-card-link">Cy</a></p></div>
<div class="member-card"><p class="name"><a href="/members/eve%40example.org/" class="member-card-link">Eve</a></p></div>
</div><span class="member-count">5 members</span><a href="?per_page=96&amp;cursor=abc%3D">Next >></a>"""
PAGE2 = """<div class="member-card"><a href="/members/dee/" class="member-card-link">Dee</a></div>
<div class="member-card"><a href="/members/ana/" class="member-card-link">Ana</a></div>"""

PROFILES = {
    "ana": {"username": "ana", "name": "Ana  Ruiz", "institutional_affiliation": "State U", "orcid": "0000-0001-2345-678X",
            "avatar": "https://hcommons.org/avatars/ana.jpg",
            "academic_interests": [{"id": 1, "text": "Science identity"}, {"id": 2, "text": "Open to collaboration"},
                                   {"id": 3, "text": "qualitative interviews"}]},
    "ben.k": {"username": "ben.k", "name": "Ben K", "academic_interests": [{"id": 4, "text": "psychometrics"}]},
    "cy": {"username": "cy", "name": "Cy", "academic_interests": []},
    "dee": {"username": "dee", "name": "Dee", "academic_interests": [{"id": 5, "text": "open to collaboration"}]},
}


def fake_get(url, accept="application/json", timeout=20):
    if "/api/v1/members/" in url:
        name = url.rstrip("/").split("/")[-1]
        return (200, json.dumps(PROFILES[name])) if name in PROFILES else (404, "")
    return (200, PAGE2) if "cursor=" in url else (200, PAGE1)


def read(names):
    return commons.iter_profiles(names, get=fake_get, workers=2)


def config(required=False, exclude=()):
    return {"message_url_template": "https://stemedplus.org/members/me/messages/compose/?r={username}",
            "listing": {"opt_in_required": required, "opt_in_interest": "open to collaboration", "exclude": list(exclude)}}


class Directory(unittest.TestCase):
    def test_reads_every_page_once(self):
        names = commons.directory_usernames(get=fake_get, pause=0)
        self.assertEqual(names, ["ana", "ben.k", "cy", "eve@example.org", "dee"])
        self.assertEqual(commons.directory_usernames.total, 5)

    def test_unusual_usernames_are_quoted(self):
        self.assertEqual(commons.profile_url("eve@example.org"),
                         "https://stemedplus.profile.hcommons.org/members/eve%40example.org/")

    def test_next_link_resolves_relative_cursor(self):
        self.assertEqual(commons.next_page(PAGE1, commons.DIRECTORY),
                         "https://stemedplus.profile.hcommons.org/members/?per_page=96&cursor=abc%3D")

    def test_empty_directory_is_an_error(self):
        with self.assertRaises(RuntimeError):
            commons.directory_usernames(get=lambda u, accept=None: (200, "<p>nothing</p>"), pause=0)


class BackwardPaging(unittest.TestCase):
    def test_members_skipped_going_forward_are_found_going_back(self):
        pages = {
            "first": '<a href="/members/a/" class="member-card-link">A</a><span class="member-count">3 members</span>'
                     '<a href="?per_page=96&amp;cursor=x">Next >></a>',
            "last": '<a href="/members/c/" class="member-card-link">C</a><a href="?per_page=96&amp;cursor=y&amp;dir=prev"><< Previous</a>',
            "back": '<a href="/members/b/" class="member-card-link">B</a><a href="/members/a/" class="member-card-link">A</a>',
        }
        def get(url, accept=None):
            return 200, pages["back" if "dir=prev" in url else "last" if "cursor=x" in url else "first"]
        self.assertEqual(sorted(commons.directory_usernames(get=get, pause=0)), ["a", "b", "c"])


class Cards(unittest.TestCase):
    def names(self, cfg):
        cards, counts = directory.collect(["ana", "ben.k", "cy", "dee", "nobody"], cfg, read)
        return [c["username"] for c in cards], cards, counts

    def test_preview_lists_everyone_with_interests(self):
        names, cards, counts = self.names(config())
        self.assertEqual(names, ["ana", "ben.k"])          # cy has none; dee has only the opt-in interest
        self.assertEqual(counts["missing"], 1)
        ana = cards[0]
        self.assertEqual(ana["interests"], ["Science identity", "qualitative interviews"])   # opt-in tag hidden
        self.assertEqual(ana["name"], "Ana Ruiz")
        self.assertTrue(ana["opted_in"])
        self.assertEqual(ana["orcid"], "0000-0001-2345-678X")

    def test_opt_in_required(self):
        names, _, _ = self.names(config(required=True))
        self.assertEqual(names, ["ana"])

    def test_exclude(self):
        names, _, _ = self.names(config(exclude=["ANA"]))
        self.assertEqual(names, ["ben.k"])


class Refresh(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()) / "data.json"

    def run_refresh(self, **kw):
        return directory.refresh(self.tmp, config(), list_members=lambda: ["ana", "ben.k", "cy", "dee"], read=read, **kw)

    def test_writes_then_no_change(self):
        changed, msg = self.run_refresh()
        self.assertTrue(changed, msg)
        self.assertEqual(len(json.loads(self.tmp.read_text())["people"]), 2)
        changed, msg = self.run_refresh()
        self.assertFalse(changed)
        self.assertIn("No change", msg)

    def test_keeps_last_copy_when_directory_fails(self):
        self.run_refresh()
        def broken():
            raise RuntimeError("member directory answered 503")
        changed, msg = directory.refresh(self.tmp, config(), list_members=broken, read=read)
        self.assertFalse(changed)
        self.assertIn("Kept the last good copy", msg)

    def test_keeps_last_copy_when_profiles_do_not_answer(self):
        self.run_refresh()
        down = lambda names: ((n, commons.UNAVAILABLE, None) for n in names)
        changed, msg = directory.refresh(self.tmp, config(), list_members=lambda: ["ana", "ben.k"], read=down)
        self.assertFalse(changed)
        self.assertEqual(len(json.loads(self.tmp.read_text())["people"]), 2)


class Page(unittest.TestCase):
    def test_build_puts_cards_in_the_page(self):
        cards, counts = directory.collect(["ana", "ben.k"], config(), read)
        out = Path(tempfile.mkdtemp())
        payload = build.build(out, config(), {"updated": "2026-11-16T00:00:00Z", "counts": counts, "people": cards})
        html = (out / "index.html").read_text()
        self.assertNotIn(build.MARK, html)
        self.assertIn('"preview":true', html)
        self.assertIn("Science identity", html)
        self.assertTrue(payload["preview"])
        self.assertTrue((out / "stemedplus-theme.css").exists())


if __name__ == "__main__":
    unittest.main()


class Organizations(unittest.TestCase):
    def test_stemedplus_card_is_valid(self):
        orgs = build.load_organizations()
        self.assertEqual(orgs[0]["name"], "STEMEd+ Commons")
        self.assertEqual(orgs[0]["contact"], "https://stemedplus.org/contact-us/")

    def test_required_fields(self):
        path = Path(tempfile.mkdtemp()) / "orgs.json"
        path.write_text(json.dumps({"organizations": [{"name": "X", "contact": "https://x.org/"}]}))
        with self.assertRaises(SystemExit):
            build.load_organizations(path)

    def test_contact_must_be_https(self):
        path = Path(tempfile.mkdtemp()) / "orgs.json"
        path.write_text(json.dumps({"organizations": [{"name": "X", "summary": "s", "contact": "mailto:a@b.org"}]}))
        with self.assertRaises(SystemExit):
            build.load_organizations(path)
