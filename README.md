# STEMEd+ Collaborators

Find people to work with in STEM+ education research, and reach them through STEMEd+ Commons:
**https://jlib271.github.io/stemed-collaborators/**

STEMEd+ Collaborators is part of [STEMEd+ Commons](https://stemedplus.hcommons.org/), with
[STEMEd+ Jobs](https://jlib271.github.io/stemed-jobs/), [STEMEd+ Funding](https://jlib271.github.io/stemed-funding/),
[STEMEd+ Conferences](https://jlib271.github.io/stemed-conferences/), the
[STEMEd+ Digest](https://jlib271.github.io/STEMEd-Digest/), and the
[STEM+ Education Research Graduate Programs](https://jlib271.github.io/stem-ed-research-programs/) list.

## How it works

- **Opt-in only.** People list themselves with the
  [Join or update the directory](https://github.com/JLib271/stemed-collaborators/issues/new?template=join_directory.yml)
  form. Everything on the form is public. Email addresses are never collected or shown.
- **Confirmed on Commons.** Before listing someone, a maintainer sends them a private message on STEMEd+ Commons
  to confirm the form is theirs. This also checks that the Commons profile link works for messaging.
- **Search by need.** The page ranks people by what the searcher needs (kind of collaboration, method, topic)
  and narrows by who (discipline, career stage, institution type). Each card says why the person matches. If the
  searcher also says what they can offer, people looking for that are marked as a two-way match.
- **Contact through Commons.** "Message on Commons" opens the person's Commons profile, where signed-in members
  can send a private message. "Copy a message starter" copies a short, editable introduction.
- **Kept current.** A profile is shown for one year after it was last confirmed. Sending the form again renews it.
  Lapsed profiles stay in `profiles/` but are left off the site; only their count is published.

## For maintainers: approving a form

1. Read the new issue. Check the Commons profile link opens the right person.
2. Send that person a private message on STEMEd+ Commons: "Did you submit a profile to STEMEd+ Collaborators?"
3. When they say yes, add the **approved** label to the issue. The
   [intake workflow](.github/workflows/intake.yml) writes `profiles/<username>.yml`, replies on the issue,
   closes it, and republishes the site. If the form has a problem, it replies with what to fix and removes the
   label instead.
4. "Remove my profile" issues work the same way. "Report a problem" issues are handled by hand.

Create these labels once (Issues → Labels): `approved`, `directory: join`, `directory: remove`,
`directory: report`. The intake also recognizes the forms without their labels.

## Join without a GitHub account

Email the maintainer, Julie Libarkin, at the address on her STEMEd+ Commons profile with the answers to the
form. She will confirm with you on STEMEd+ Commons and add you.

## Files

- `profiles/*.yml`: one file per person, named by Commons username.
- `config/vocab.json`: career stages, institution types, methods, and kinds of collaboration. After changing it,
  run `python -m stemed_collaborators.forms --write` to regenerate the issue forms (a test checks they match).
- Disciplines come from the list shared across STEMEd+ Commons, kept in
  [HuMeta](https://github.com/JLib271/HuMeta) (`standard/humeta/stemedplus_disciplines.json`).
- `config/site.json`: `message_url_template` is the "compose a message" link on STEMEd+ Commons, with
  `{username}` where the person's username goes. `members/me/` stands for whoever is signed in, so the link
  works for any sender (people who are not signed in are asked to sign in first). Empty it to make
  "Message on Commons" open the person's profile instead.

## Run it locally

    pip install -r requirements.txt
    python -m unittest discover -s tests -t .
    python -m stemed_collaborators --validate
    python -m stemed_collaborators --out output      # then open output/index.html through a local web server

The test profiles in `tests/fixtures/profiles/` are fictional and are never published.

## License

Code: MIT. Manrope font: SIL Open Font License (`site/manrope-OFL.txt`).
