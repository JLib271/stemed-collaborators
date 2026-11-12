# STEMEd+ Collaborators

Find people to work with across STEM+ education research and practice (researchers, K-12 teachers, college
instructors, and informal educators), and reach them through STEMEd+ Commons:
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
- **Filled in from Commons.** People give their STEMEd+ Commons username; their name, institution, ORCID iD,
  and photo come from their public Commons profile unless they fill them in on the form
  (`stemed_collaborators/commons.py`, reading `stemedplus.profile.hcommons.org/api/v1/members/<username>/`).
  The same check turns away accounts that have not joined STEMEd+. If Commons does not answer, the form's
  own answers are used, and a daily step adds photos later.
- **Confirmed on Commons.** Before listing someone, a maintainer sends them a private message on STEMEd+ Commons
  to confirm the form is theirs. This also checks that the Commons profile link works for messaging.
- **Search by need.** The page ranks people by what the searcher needs (kind of collaboration, method, topic)
  and narrows by who (discipline, career stage, institution type). Each card says why the person matches. If the
  searcher also says what they can offer, people looking for that are marked as a two-way match.
- **Contact through Commons.** "Message on STEMEd+ Commons" opens a new private message to the person (sign in
  first if asked). "Copy a message starter" copies a short, editable introduction.
- **Kept current.** Every day, [the yearly check](.github/workflows/reminders.yml) messages people on STEMEd+
  Commons 12 months after they last confirmed ("reply KEEP to stay listed"), sends a last reminder at 14 months,
  and removes the profile at 15 months. A KEEP reply, the [Keep my profile](https://github.com/JLib271/stemed-collaborators/issues/new?template=keep_profile.yml)
  form, or sending the join form again renews it for a year. Anything that needs a person is posted on the
  "Yearly profile check" issue.

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

## Setting up the yearly messages

Messages are sent, and KEEP replies read, through the STEMEd+ Commons API, signed in as one Commons account.
A separate account (for example "STEMEd+ Collaborators") is best, so replies don't land in your own inbox.

1. Sign in to stemedplus.org as that account, go to `wp-admin/profile.php`, and under **Application
   Passwords** create one named "stemed-collaborators".
2. In this repository, add two secrets (Settings -> Secrets and variables -> Actions):
   `COMMONS_USER` (the account's username) and `COMMONS_APP_PASSWORD` (the password from step 1).
3. Run **Yearly profile check** once from the Actions tab to test it.

Until the secrets are set, nothing is sent: the "Yearly profile check" issue lists who is due, with a link that
starts each message, and removals still happen at 15 months.

## Join without a GitHub account

People without a GitHub account use the form on stemedplus.org, which emails each submission to the
maintainer. To list them:

1. Open a new issue with the **Add someone from the STEMEd+ form (maintainers)** template.
2. Paste the whole notification email, add the person's name to the title, and submit.
3. Confirm with them on STEMEd+ Commons and add the **approved** label, as for any join form.

The intake reads the email by its field names, so the stemedplus.org form must use the names and choices in
[docs/stemedplus-form.md](docs/stemedplus-form.md) (generated from `config/vocab.json`). Once the form is live,
put its address in `config/site.json` as `join_form_url`: "Join the directory" then opens it, with
"Join with GitHub" beside it.

## Files

- `profiles/*.yml`: one file per person, named by Commons username.
- `config/vocab.json`: career stages, institution types, methods, and kinds of collaboration. After changing it,
  run `python -m stemed_collaborators.forms --write` to regenerate the issue forms and
  `docs/stemedplus-form.md` (a test checks they match), and update the stemedplus.org form to match.
- Disciplines come from the list shared across STEMEd+ Commons, kept in
  [HuMeta](https://github.com/JLib271/HuMeta) (`standard/humeta/stemedplus_disciplines.json`).
- `config/site.json`: `message_url_template` is the "compose a message" link on STEMEd+ Commons, with
  `{username}` where the person's username goes. `members/me/` stands for whoever is signed in, so the link
  works for any sender (people who are not signed in are asked to sign in first). Empty it to make
  "Message on STEMEd+ Commons" open the person's profile instead.

## Run it locally

    pip install -r requirements.txt
    python -m unittest discover -s tests -t .
    python -m stemed_collaborators --validate
    python -m stemed_collaborators --out output      # then open output/index.html through a local web server

The test profiles in `tests/fixtures/profiles/` are fictional and are never published.

## License

Code: MIT. Manrope font: SIL Open Font License (`site/manrope-OFL.txt`).
