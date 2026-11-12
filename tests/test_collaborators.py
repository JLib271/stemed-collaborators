import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path

import yaml

from stemed_collaborators import build, forms, intake, profiles

FIX = Path(__file__).parent / "fixtures" / "profiles"
TODAY = dt.date(2026, 11, 10)


def filled_form(**over):
    """An issue body the way GitHub renders the join form."""
    ticks = lambda opts, chosen: "\n".join(f"- [{'X' if o in chosen else ' '}] {o}" for o in opts)  # noqa: E731
    v = profiles.VOCAB
    answers = {
        "name": "Cara Formfill", "username": "cara-f", "commons_profile": "https://hcommons.org/members/cara-f/",
        "pronouns": "_No response_", "career_stage": "Postdoc", "institution": "Example University",
        "institution_types": ticks(v["institution_types"], ["Research university"]),
        "disciplines": ticks(forms.DISCIPLINES, ["Physics", "Learning Science"]),
        "methods": ticks(v["methods"], ["Mixed methods"]),
        "topics": "modeling, labs ,  ", "offers": ticks(v["collaboration"], ["Co-author on a paper"]),
        "seeking": ticks(v["collaboration"], ["Mentor"]),
        "about": "I study\n  physics labs.", "orcid": "https://orcid.org/0000-0002-1825-0097",
        "consent": ticks(forms.CONSENT, forms.CONSENT),
    }
    answers.update(over)
    return "\n\n".join(f"### {forms.LABELS[k]}\n\n{answers[k]}" for k in forms.LABELS)


class ProfilesTest(unittest.TestCase):
    def test_fixtures_valid(self):
        entries, problems = profiles.load(FIX)
        self.assertEqual(problems, [])
        self.assertEqual(len(entries), 3)

    def test_rejects_bad_values(self):
        _, data = profiles.load(FIX)[0][0]
        bad = dict(data, commons_profile="https://evil.example/hcommons.org", methods=["Astrology"], extra=1)
        p = profiles.check(bad, data["username"])
        self.assertTrue(any("commons_profile" in x for x in p))
        self.assertTrue(any("Astrology" in x for x in p))
        self.assertTrue(any("unknown field" in x for x in p))
        self.assertTrue(profiles.check(dict(data, username="other"), data["username"]))
        self.assertTrue(profiles.check(dict(data, about="x" * 401), data["username"]))
        self.assertFalse(profiles.is_commons_url("https://hcommons.org.evil.com/x"))
        self.assertTrue(profiles.is_commons_url("https://stemedplus.hcommons.org/members/a/"))

    def test_lapsed_profiles_hidden(self):
        with tempfile.TemporaryDirectory() as tmp:
            payload = build.run(Path(tmp), TODAY, folder=FIX)
            ids = [p["id"] for p in payload["people"]]
            self.assertEqual(ids, ["test-ana", "test-ben"])
            self.assertEqual(payload["lapsed"], 1)
            self.assertNotIn("test-old", (Path(tmp) / "collaborators.json").read_text())
            for name in ("index.html", "stemedplus-theme.css", "manrope.woff"):
                self.assertTrue((Path(tmp) / name).exists())
            json.loads((Path(tmp) / "collaborators.json").read_text())


class FormsTest(unittest.TestCase):
    def test_forms_match_vocab(self):
        root = forms.TEMPLATES
        for name, text in forms.render_forms().items():
            on_disk = (root / name).read_text(encoding="utf-8").split("\n", 1)[1]
            self.assertEqual(on_disk, text, f"{name} is out of date: run python -m stemed_collaborators.forms --write")

    def test_website_spec_up_to_date(self):
        self.assertEqual(forms.SPEC.read_text(encoding="utf-8"), forms.website_form_spec(),
                         "run python -m stemed_collaborators.forms --write")

    def test_pasted_website_email(self):
        email = "\n".join([
            "New submission from STEMEd+ Collaborators", "",
            "Your name as you want it shown: Dana Pastewell",
            "Your STEMEd+ Commons username: dpaste",
            "Link to your STEMEd+ Commons profile",
            "https://stemedplus.profile.hcommons.org/members/dpaste/",
            "Pronouns: they/them",
            "Career stage: Postdoc",
            "Institution type",
            "Minority-serving institution (HSI, HBCU, TCU, AANAPISI, or other MSI)",
            "Community or technical college",
            "Disciplines: Physics, Learning Science",
            "Methods you work with: Mixed methods, Design-based research",
            "Topics you work on: lab courses, belonging",
            "What you can offer others: Methods partner",
            "What you are looking for:",
            "About: I study",
            "two-year physics labs.",
            "Consent: " + ", ".join(forms.CONSENT),
        ])
        body = f"### {forms.PASTE_LABEL}\n\n```text\n{email}\n```"
        self.assertEqual(forms.form_kind(body, []), "join")
        self.assertEqual(forms.username_from_issue(body), "dpaste")
        username, data, problems = forms.profile_from_issue(body, TODAY)
        self.assertEqual(problems, [])
        self.assertEqual(data["institution_types"], profiles.VOCAB["institution_types"][0:1] + ["Community or technical college"])
        self.assertEqual(data["disciplines"], ["Learning Science", "Physics"] if forms.DISCIPLINES.index("Learning Science") < forms.DISCIPLINES.index("Physics") else ["Physics", "Learning Science"])
        self.assertEqual(data["methods"], ["Mixed methods", "Design-based research"])
        self.assertEqual(data["topics"], ["lab courses", "belonging"])
        self.assertNotIn("seeking", data)
        self.assertEqual(data["about"], "I study two-year physics labs.")
        _, _, problems = forms.profile_from_paste(email.replace(forms.CONSENT[2], ""), TODAY)
        self.assertTrue(any("consent" in p for p in problems))

    def test_option_labels_have_no_markdown_trouble(self):
        for opts in (profiles.VOCAB["methods"], profiles.VOCAB["collaboration"], profiles.VOCAB["institution_types"]):
            for o in opts:
                self.assertNotIn("\n", o)
                self.assertFalse(o.startswith(("-", "#")))

    def test_parse_join_form(self):
        username, data, problems = forms.profile_from_issue(filled_form(), TODAY)
        self.assertEqual(problems, [])
        self.assertEqual(username, "cara-f")
        self.assertEqual(sorted(data["disciplines"]), ["Learning Science", "Physics"])
        self.assertEqual(data["topics"], ["modeling", "labs"])
        self.assertEqual(data["about"], "I study physics labs.")
        self.assertEqual(data["orcid"], "0000-0002-1825-0097")
        self.assertNotIn("pronouns", data)
        self.assertEqual(data["confirmed"], TODAY)

    def test_offering_only(self):
        blank = "\n".join(f"- [ ] {o}" for o in profiles.VOCAB["collaboration"])
        username, data, problems = forms.profile_from_issue(filled_form(seeking=blank), TODAY)
        self.assertEqual(problems, [])
        self.assertNotIn("seeking", data)
        self.assertEqual(profiles.to_record(username, data, TODAY)["seeking"], [])
        _, _, problems = forms.profile_from_issue(filled_form(offers=blank), TODAY)
        self.assertTrue(any("offers" in p for p in problems))

    def test_consent_required(self):
        _, _, problems = forms.profile_from_issue(filled_form(consent="- [X] " + forms.CONSENT[0]), TODAY)
        self.assertTrue(any("consent" in p for p in problems))

    def test_form_kind_without_labels(self):
        self.assertEqual(forms.form_kind(filled_form(), []), "join")
        body = f"### {forms.LABELS['username']}\n\ncara-f\n\n### {forms.REMOVE_NOTE}\n\n_No response_"
        self.assertEqual(forms.form_kind(body, []), "remove")
        self.assertEqual(forms.form_kind("hello", []), "")


class IntakeTest(unittest.TestCase):
    def test_join_update_remove(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            changed, user, reply = intake.handle(filled_form(), ["directory: join"], dt.date(2026, 1, 5), folder)
            self.assertTrue(changed, reply)
            saved = yaml.safe_load((folder / "cara-f.yml").read_text())
            self.assertEqual(profiles.check(saved, "cara-f"), [])
            # An update keeps the first listed date and moves the confirmed date.
            changed, _, reply = intake.handle(filled_form(name="Cara F."), ["directory: join"], TODAY, folder)
            saved = yaml.safe_load((folder / "cara-f.yml").read_text())
            self.assertIn("Updated", reply)
            self.assertEqual((saved["name"], saved["listed"], saved["confirmed"]), ("Cara F.", dt.date(2026, 1, 5), TODAY))
            body = f"### {forms.LABELS['username']}\n\ncara-f\n\n### {forms.REMOVE_NOTE}\n\n_No response_"
            changed, _, _ = intake.handle(body, ["directory: remove"], TODAY, folder)
            self.assertTrue(changed)
            self.assertFalse((folder / "cara-f.yml").exists())

    def test_bad_form_not_written(self):
        with tempfile.TemporaryDirectory() as tmp:
            changed, _, reply = intake.handle(filled_form(commons_profile="http://example.com"), ["directory: join"], TODAY, Path(tmp))
            self.assertFalse(changed)
            self.assertIn("commons_profile", reply)
            self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_remove_cannot_escape_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            body = f"### {forms.LABELS['username']}\n\n../../etc/passwd\n\n### {forms.REMOVE_NOTE}\n\nx"
            changed, _, _ = intake.handle(body, ["directory: remove"], TODAY, Path(tmp))
            self.assertFalse(changed)
            body = filled_form(username="../evil")
            changed, _, _ = intake.handle(body, ["directory: join"], TODAY, Path(tmp))
            self.assertFalse(changed)


if __name__ == "__main__":
    unittest.main()


class FakeCommons:
    """Stands in for the STEMEd+ Commons API."""

    def __init__(self, ids, keeps=None):
        self.ids, self.keeps, self.sent = ids, keeps or {}, []

    def user_id(self, username):
        return self.ids.get(username)

    def send(self, username, subject, message):
        if username not in self.ids:
            return False
        self.sent.append((username, subject))
        return True

    def keep_replies(self, since):
        return {uid: d for uid, d in self.keeps.items() if d >= since}


class RemindersTest(unittest.TestCase):
    def setUp(self):
        import shutil
        self.tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self.tmp.name)
        for f in FIX.glob("*.yml"):
            shutil.copy(f, self.folder)

    def tearDown(self):
        self.tmp.cleanup()

    def load(self, slug):
        return yaml.safe_load((self.folder / f"{slug}.yml").read_text())

    def test_schedule(self):
        from stemed_collaborators import reminders
        ana_confirmed = self.load("test-ana")["confirmed"]
        fake = FakeCommons({"test-ana": 1, "test-ben": 2, "test-old": 3})
        day = lambda n: ana_confirmed + dt.timedelta(days=n)  # noqa: E731
        reminders.run(day(364), fake, self.folder)
        self.assertNotIn("test-ana", [u for u, _ in fake.sent])
        reminders.run(day(365), fake, self.folder)
        self.assertIn(("test-ana", "Keep your STEMEd+ Collaborators profile?"), fake.sent)
        self.assertEqual(self.load("test-ana")["reminded"], [day(365)])
        n = len(fake.sent)
        reminders.run(day(366), fake, self.folder)            # no second first-reminder
        self.assertEqual([u for u, _ in fake.sent[n:]].count("test-ana"), 0)
        reminders.run(day(425), fake, self.folder)
        self.assertEqual(fake.sent[-1][1] if fake.sent[-1][0] == "test-ana" else
                         [s for u, s in fake.sent if u == "test-ana"][-1], "Last reminder: your STEMEd+ Collaborators profile")
        reminders.run(day(455), fake, self.folder)
        self.assertFalse((self.folder / "test-ana.yml").exists())
        self.assertIn(("test-ana", "Your STEMEd+ Collaborators profile was removed"), fake.sent)

    def test_keep_reply_renews(self):
        from stemed_collaborators import reminders
        confirmed = self.load("test-ana")["confirmed"]
        day = lambda n: confirmed + dt.timedelta(days=n)  # noqa: E731
        fake = FakeCommons({"test-ana": 1})
        reminders.run(day(365), fake, self.folder)
        fake.keeps = {1: day(370)}
        lines = reminders.run(day(371), fake, self.folder)
        data = self.load("test-ana")
        self.assertEqual(data["confirmed"], day(371))
        self.assertNotIn("reminded", data)
        self.assertTrue(any("Renewed `test-ana`" in l for l in lines))

    def test_without_commons_lists_people_and_still_removes(self):
        from stemed_collaborators import reminders
        old = self.load("test-old")["confirmed"]
        lines = reminders.run(old + dt.timedelta(days=455), None, self.folder)
        self.assertFalse((self.folder / "test-old.yml").exists())
        self.assertTrue(any("Removed `test-old`" in l and "members/me/messages/compose/?r=test-old" in l for l in lines))
        lines = reminders.run(self.load("test-ana")["confirmed"] + dt.timedelta(days=365), None, self.folder)
        self.assertTrue(any("first reminder for `test-ana`" in l and "messages are not set up" in l for l in lines))

    def test_keep_form(self):
        body = f"### {forms.LABELS['username']}\n\ntest-ben\n\n### {forms.KEEP_NOTE}\n\n_No response_"
        self.assertEqual(forms.form_kind(body, []), "keep")
        data = self.load("test-ben"); data["reminded"] = [TODAY]
        (self.folder / "test-ben.yml").write_text(yaml.safe_dump(data))
        changed, _, reply = intake.handle(body, ["directory: keep"], TODAY, self.folder)
        self.assertTrue(changed, reply)
        data = self.load("test-ben")
        self.assertEqual(data["confirmed"], TODAY)
        self.assertNotIn("reminded", data)


class CommonsLookupTest(unittest.TestCase):
    def info(self, **over):
        d = {"username": "cara-f", "name": "Cara Formfill", "institutional_affiliation": "Example State University",
             "orcid": "0000-0002-1825-0097", "avatar": "https://hcommons.org/app/uploads/avatars/1/abc-bpfull.jpg",
             "memberships": {"STEMED+": True, "MLA": False}}
        d.update(over)
        return d

    def test_blanks_filled_from_commons(self):
        from stemed_collaborators import commons
        body = filled_form(name="_No response_", institution="_No response_", orcid="_No response_",
                           commons_profile="_No response_")
        _, data, problems = forms.profile_from_issue(body, TODAY, lookup=lambda u: (commons.OK, self.info()))
        self.assertEqual(problems, [])
        self.assertEqual(data["name"], "Cara Formfill")
        self.assertEqual(data["institution"], "Example State University")
        self.assertEqual(data["orcid"], "0000-0002-1825-0097")
        self.assertEqual(data["commons_profile"], "https://stemedplus.profile.hcommons.org/members/cara-f/")
        self.assertTrue(data["photo"].endswith("abc-bpfull.jpg"))

    def test_form_answers_win(self):
        from stemed_collaborators import commons
        _, data, _ = forms.profile_from_issue(filled_form(), TODAY, lookup=lambda u: (commons.OK, self.info()))
        self.assertEqual((data["name"], data["institution"]), ("Cara Formfill", "Example University"))

    def test_not_a_member_or_no_account(self):
        from stemed_collaborators import commons
        _, _, problems = forms.profile_from_issue(
            filled_form(), TODAY, lookup=lambda u: (commons.OK, self.info(memberships={"STEMED+": False})))
        self.assertTrue(any("has not joined STEMEd+" in p for p in problems))
        _, _, problems = forms.profile_from_issue(filled_form(), TODAY, lookup=lambda u: (commons.MISSING, None))
        self.assertTrue(any("No STEMEd+ Commons account" in p for p in problems))

    def test_commons_down_falls_back_to_form(self):
        from stemed_collaborators import commons
        down = lambda u: (commons.UNAVAILABLE, None)  # noqa: E731
        _, data, problems = forms.profile_from_issue(filled_form(), TODAY, lookup=down)
        self.assertEqual(problems, [])
        _, _, problems = forms.profile_from_issue(filled_form(name="_No response_"), TODAY, lookup=down)
        self.assertTrue(any("name" in p for p in problems))

    def test_whole_profile_link_as_username(self):
        _, data, problems = forms.profile_from_issue(
            filled_form(username="https://stemedplus.profile.hcommons.org/members/cara-f/"), TODAY)
        self.assertEqual((data["username"], problems), ("cara-f", []))

    def test_photo_urls(self):
        self.assertTrue(profiles.is_photo_url("https://hcommons.org/app/uploads/avatars/1027794/1680622545-bpfull.jpg"))
        self.assertFalse(profiles.is_photo_url("https://evil.example/x.jpg"))
        self.assertFalse(profiles.is_photo_url("https://hcommons.org/mystery-man.jpg"))
        self.assertFalse(profiles.is_photo_url('https://hcommons.org/a".jpg'))


class BackfillTest(unittest.TestCase):
    def test_backfill_photos(self):
        import shutil
        from stemed_collaborators import commons
        with tempfile.TemporaryDirectory() as tmp:
            for f in FIX.glob("*.yml"):
                shutil.copy(f, tmp)
            photo = "https://hcommons.org/app/uploads/avatars/9/x-bpfull.jpg"
            lookup = lambda u: (commons.OK, {"avatar": photo}) if u == "test-ana" else (commons.UNAVAILABLE, None)  # noqa: E731
            self.assertEqual(commons.backfill_photos(tmp, lookup), ["test-ana"])
            self.assertEqual(yaml.safe_load((Path(tmp) / "test-ana.yml").read_text())["photo"], photo)
            self.assertEqual(commons.backfill_photos(tmp, lookup), [])


class TeachingMentorTests(unittest.TestCase):
    def test_teaching_mentor_is_an_offer_and_seek_option(self):
        self.assertIn("Teaching mentor or peer observer", profiles.VOCAB["collaboration"])
        page = (Path(__file__).resolve().parent.parent / "site" / "index.html").read_text(encoding="utf-8")
        self.assertIn("?need=Teaching+mentor+or+peer+observer", page)
        self.assertIn("teaching_circles", page)
