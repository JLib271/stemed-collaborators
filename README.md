# Find Collaborators (STEMEd+ Commons)

Find people to work with across STEM+ teaching and STEM+ education research, by the interests and skills on their
**STEMEd+ Commons profiles**. Part of [STEMEd+ Commons](https://stemedplus.org/).

There is no separate sign-up. People are listed by filling in their own Commons profile, and the page
updates itself every day.

## How it works

1. **Who's a member.** Every day, GitHub reads the public
   [STEMEd+ member directory](https://stemedplus.profile.hcommons.org/members/) for usernames.
2. **What they've shared.** For each member it reads their public profile: name, institution, ORCID iD,
   photo, and **academic interests**.
3. **Who gets a card.** Members with at least one academic interest.
4. **Search.** The page searches interests, skills, names, and institutions. Clicking an interest shows
   everyone else with it, and the most common interests are listed as one-click searches.
5. **Getting listed.** The page invites people to sign in, open **Edit profile**, and add academic
   interests, including their skills and methods. Their card appears at the next daily update.
6. **Contact.** Each card links to the person's profile, where they list the ways to reach them. (Knowledge
   Commons no longer has direct messages.)

Only public profile fields are used. Nothing is collected from people directly.

## Organizations (config/organizations.json)

Organizations open to collaboration get their own cards, shown first and marked "Organization": a summary,
what they are looking for, searchable interest tags, a "Contact to collaborate" link, and their website.
Organizations ask to be added through the [STEMEd+ contact page](https://stemedplus.org/contact-us/), which the
page links to; a maintainer then adds an entry. Required: `name`, `summary`, `contact` (https). A `logo` is a
file in `site/` or an https address. The page has an Everyone / People / Organizations switch.

## Who is listed (config/site.json)

Everyone in the STEMEd+ member directory with academic interests on their profile gets a card. Cards show
only public profile fields; people get in touch through the contact links on each profile. To come off the page, a
member removes their academic interests, or a maintainer adds their username to `listing.exclude`.

`listing.opt_in_required` (default `false`) can list only members whose interests include
`listing.opt_in_interest` ("open to collaboration"); the page then asks people to add it.

## Publishing

`.github/workflows/update.yml` runs daily, on every push to `main`, and from the Actions tab. It saves the
cards in `data/collaborators.json` when they change, builds the page, and publishes it to GitHub Pages while
`publish` in `config/site.json` is `true`. Turn on once: **Settings → Pages → Source: GitHub Actions**. On a free GitHub
account, Pages needs the repository to be public.

## When Commons doesn't answer

The directory page and profile address are public but not documented, and Knowledge Commons is still
changing its profile system. If the directory can't be read, fewer than 80% of profiles answer, or the
number of cards falls by more than half, the last good copy is kept and the run log says why. If a big drop
is real, run `python -m stemed_collaborators --refresh --force` once.

## Files

- `stemed_collaborators/commons.py`: reads the member directory and profiles.
- `stemed_collaborators/directory.py`: decides who gets a card and keeps the last good copy.
- `stemed_collaborators/build.py`: builds `index.html` with the cards built in.
- `site/index.html`: the page (search, cards, invitation). The green band and footer come from
  [stemedplus-theme](https://github.com/JLib271/stemedplus-theme); don't edit them here.
- `data/collaborators.json`: the saved cards.
- `tests/`: `python -m unittest discover -s tests -t .`
