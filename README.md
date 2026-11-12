# ADEA website

This repository contains the website of the Australasian Development Economics Association (ADEA), [ausdevea.org](https://ausdevea.org).
Every page comes from a plain-text file here, so committee members can update the site in GitHub's web editor without installing anything.

## Updating the site

Open the file that you want to change on GitHub, click the pencil icon, make your edit, and commit it.
You need write access to the repository to commit.
The commit must go to the `main` branch, which is GitHub's default ("Commit directly to the main branch").
GitHub then rebuilds the site, and the change appears within a few minutes.
If the build fails, for example after a typo in `data/members.json`, the site stays as it was.

### Page text

Each page has its own file in [`content/`](content/):

| Page | File |
|------|------|
| Home | `content/home.md` |
| About | `content/about.md` |
| News and events (page heading and intro text only) | `content/news.md` |
| Research | `content/stories.md` |
| Members | `content/members.md` |
| Join or renew | `content/join.md` |

The footer, with the contact email, the ABN, and the links to related networks, is in `templates/partials/footer.html`.

### News and events

Each news item has its own file in the [`content/news/`](content/news/) folder.
Never add an item to `content/news.md`, which contains only the news page's own heading and intro text.
To add an item, copy an existing file such as `content/news/adew-2027.md`, give the copy a new name, and change its title, date, excerpt, and text.
The new file's name becomes the page's web address.
The excerpt is the summary that the news page and the home page show.
Write the date as YYYY-MM-DD, for example 2026-11-06, or the build fails.
The site lists items by date, newest first.

### Research by members

The research page features work by ADEA members only.
`content/stories.md` lists short policy pieces on outlets such as VoxDev and the Devpolicy Blog, one line per piece.
The site shows the lines in file order, so put each new piece at the top.
The top three lines also appear on the home page.
Each line has the fields `title`, `url`, `outlet`, `date`, `authors`, and `members`.
The `members` field lists only the co-authors who are ADEA members.
Write each one as the `slug` of their entry in `data/members.json`, for example `[ricardo-dahis]`.
The site bolds a member's name when their surname in `authors` matches the last part of their slug, and it shows their photo only if their entry has a `photo`.

### Members

Member profiles are in [`data/members.json`](data/members.json), in three lists: `leadership`, `members`, and `phd_students`.
To add a member, copy an existing entry in the right list and change its `name`, `slug`, `institution`, `topics`, `countries`, and `link`.
The copy keeps the other member's `slug`, so write the new one as the lowercase name with hyphens, for example `ian-anderson`.
Upload the headshot to `assets/images/members/` on GitHub with "Add file" > "Upload files".
Then set `photo` to its path inside `assets/images/`, for example `members/ian-anderson.jpg`.

### Membership payments

The buttons on the Join page open payment pages in ADEA's Stripe account.
The Stripe payment links (web addresses) are in `content/join.md`.

## Previewing changes on your own computer

You only need the local preview to check a larger change before committing it.
It needs Python and a copy of the repository on your computer.

```bash
pip install jinja2 markdown pyyaml
python scripts/build_site.py
```

The build writes the site to `_site/`; open `_site/index.html` in a browser.
