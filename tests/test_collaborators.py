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
