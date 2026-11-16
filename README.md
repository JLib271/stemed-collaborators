# Find Collaborators (STEMEd+ Commons)

Find people to work with across STEM+ education research and practice, by the interests and skills on their
**STEMEd+ Commons profiles**. Part of [STEMEd+ Commons](https://stemedplus.org/).

There is no separate sign-up. People are listed by filling in their own Commons profile, and the page
updates itself every day.

## How it works

1. **Who's a member.** Every day, GitHub reads the public
   [STEMEd+ member directory](https://stemedplus.profile.hcommons.org/members/) for usernames.
2. **What they've shared.** For each member it reads their public profile: name, institution, ORCID iD,
   photo, and **academic interests**.
3. **Who gets a card.** Members with at least one academic interest, as long as they've opted in (below).
4. **Search.** The page searches interests, skills, names, and institutions. Clicking an interest shows
   everyone else with it, and the most common interests are listed as one-click searches.
5. **Getting listed.** The page invites people to sign in, open **Edit profile**, and add academic
   interests, including their skills and methods. Their card appears at the next daily update.
6. **Contact.** Each card links to the person's profile and to a STEMEd+ Commons private message.

Only public profile fields are used. Nothing is collected from people directly.

## Opt-in (config/site.json → `listing`)

| Setting | What it does |
|---|---|
| `opt_in_required: false` | **Preview (now).** Everyone in STEMEd+ with interests counts as opted in. The page says so in a yellow bar, and it is **not published** to GitHub Pages. |
| `opt_in_required: true` | **Launch.** Only members whose academic interests include `opt_in_interest` are listed. The invitation then asks people to add it. That interest is not shown on cards. |
| `opt_in_interest` | The interest that means "list me". Default `open to collaboration`. |
| `exclude` | Usernames never listed, for anyone who asks to be left out. |

Leaving is simple: remove the opt-in interest (or all interests) from your profile. The card goes at the
next update.

## Seeing the page during preview

Open **Actions → Update and publish →** the latest run → **find-collaborators-page** under Artifacts.
Unzip it and open `index.html`: the cards are built into the page, so it works straight from your computer.

## Publishing

`.github/workflows/update.yml` runs daily, on every push to `main`, and from the Actions tab. It saves the
cards in `data/collaborators.json` when they change, builds the page, and publishes it to GitHub Pages once
`opt_in_required` is `true`. Turn on once: **Settings → Pages → Source: GitHub Actions**. On a free GitHub
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
