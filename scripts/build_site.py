"""Render the ADEA static site: Markdown content + Jinja2 templates -> _site/.

Editors only ever touch the Markdown in content/. This script (and the GitHub
Actions workflow that runs it) turns that into the deployed HTML. Run locally with
`python scripts/build_site.py` to preview; output lands in _site/.
"""
import os
import re
import json
import unicodedata
import shutil
import datetime
import markdown
import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT = os.path.join(ROOT, "content")
TEMPLATES = os.path.join(ROOT, "templates")
ASSETS = os.path.join(ROOT, "assets")
OUT = os.path.join(ROOT, "_site")

SITE = {
    "name": "Australasian Development Economics Association",
    "short": "ADEA",
    "description": "A non-profit community of researchers advancing development "
                   "economics across the Australasian region.",
    # public address with trailing slash; used for sitemap.xml and robots.txt
    "url": "https://australasian-devecon-association.github.io/adea-website/",
}
# Build year is passed in so the result is deterministic in CI.
YEAR = datetime.date.today().year

md = markdown.Markdown(extensions=["extra", "sane_lists"])
env = Environment(
    loader=FileSystemLoader(TEMPLATES),
    autoescape=select_autoescape(["html"]),
    trim_blocks=True,
    lstrip_blocks=True,
)


def parse_frontmatter(path):
    """Return (meta_dict, markdown_body) for a file beginning with a --- block."""
    text = open(path, encoding="utf-8").read()
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", text, re.DOTALL)
    if not m:
        return {}, text
    meta = yaml.safe_load(m.group(1)) or {}
    return meta, m.group(2)


def render_body(body):
    md.reset()
    return md.convert(body.strip()) if body.strip() else ""


def display_date(value):
    if not value:
        return ""
    if isinstance(value, datetime.date):
        d = value
    else:
        d = datetime.date.fromisoformat(str(value))
    return f"{d.day} {d.strftime('%B %Y')}"


def first_paragraph(body):
    for block in body.strip().split("\n\n"):
        block = block.strip()
        if block and not block.startswith(("#", "-", ">", "!")):
            return re.sub(r"\s+", " ", block)
    return ""


def load_news():
    """Load news posts, newest first, with url/date_display/excerpt and prev/next."""
    posts = []
    news_dir = os.path.join(CONTENT, "news")
    for fn in os.listdir(news_dir):
        if not fn.endswith(".md"):
            continue
        meta, body = parse_frontmatter(os.path.join(news_dir, fn))
        slug = os.path.splitext(fn)[0]
        meta["url"] = f"news/{slug}.html"
        meta["slug"] = slug
        meta["body"] = body
        meta["date_display"] = display_date(meta.get("date"))
        meta.setdefault("excerpt", first_paragraph(body))
        posts.append(meta)
    posts.sort(key=lambda p: str(p.get("date", "")), reverse=True)
    # wire prev (older) / next (newer) for in-article navigation
    for i, p in enumerate(posts):
        p["next"] = posts[i - 1] if i > 0 else None          # newer
        p["prev"] = posts[i + 1] if i < len(posts) - 1 else None  # older
    return posts


def write(out_relpath, html):
    dst = os.path.join(OUT, out_relpath)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(dst, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  wrote {out_relpath}")


def rel_for(out_relpath):
    """Path back to site root from a given output file (for asset/links)."""
    depth = out_relpath.count("/")
    return "../" * depth


# the member form stored ISO codes ("Monash University, AUS"); show country names instead
COUNTRY_CODES = {"AUS": None, "GBR": "United Kingdom", "USA": "United States",
                 "VNM": "Vietnam", "LKA": "Sri Lanka", "IND": "India"}


def plain_affiliation(text):
    """Replace a trailing ISO country code; Australian affiliations drop it."""
    m = re.match(r"^(.*), ([A-Z]{3})$", text)
    if not m or m.group(2) not in COUNTRY_CODES:
        return text
    country = COUNTRY_CODES[m.group(2)]
    return f"{m.group(1)}, {country}" if country else m.group(1)


def surname_key(m):
    """Sort by surname (last word of the name) unless the record sets sort_name."""
    name = m.get("sort_name") or m["name"].split()[-1]
    plain = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return (plain.lower(), m["name"].lower())


def apply_facet_map(data):
    """Relabel member-entered topics and countries through data/facet_map.json."""
    path = os.path.join(ROOT, "data", "facet_map.json")
    if not os.path.exists(path):
        return
    fmap = json.load(open(path, encoding="utf-8"))
    for field in ("topics", "countries"):
        labels = set()
        for group in ("leadership", "members", "phd_students"):
            for m in data.get(group, []):
                out = []
                for raw in m.get(field) or []:
                    label = fmap[field].get(raw, raw)
                    if label and label not in out:
                        out.append(label)
                m[field] = out
                labels.update(out)
        data[field] = sorted(labels, key=str.lower)


def load_members():
    path = os.path.join(ROOT, "data", "members.json")
    if not os.path.exists(path):
        return {"leadership": [], "members": [], "directory": [], "topics": [], "countries": []}
    data = json.load(open(path, encoding="utf-8"))
    for group in ("leadership", "members", "phd_students"):
        for m in data.get(group, []):
            if m.get("institution"):
                m["institution"] = plain_affiliation(m["institution"])
    apply_facet_map(data)
    data["members"] = sorted(data.get("members", []), key=surname_key)
    data["phd_students"] = sorted(data.get("phd_students", []), key=surname_key)
    # the directory lists everyone except PhD members, leadership included
    data["directory"] = sorted(data.get("leadership", []) + data["members"], key=surname_key)
    return data


def load_stories():
    """Load research stories, newest first, with url/date_display/excerpt."""
    stories = []
    sdir = os.path.join(CONTENT, "stories")
    if not os.path.isdir(sdir):
        return stories
    for fn in os.listdir(sdir):
        if not fn.endswith(".md"):
            continue
        meta, body = parse_frontmatter(os.path.join(sdir, fn))
        slug = os.path.splitext(fn)[0]
        meta["url"] = f"stories/{slug}.html"
        meta["body"] = body
        meta["date_display"] = display_date(meta.get("date"))
        meta.setdefault("excerpt", first_paragraph(body))
        stories.append(meta)
    stories.sort(key=lambda p: str(p.get("date", "")), reverse=True)
    return stories


def render_page(meta, body, out_relpath, news=None, members_data=None, stories=None):
    template = env.get_template(meta["template"] + ".html")
    html = template.render(
        site=SITE, page=meta, body=render_body(body),
        news=news or [], members_data=members_data or {}, stories=stories or [],
        year=YEAR, rel=rel_for(out_relpath),
    )
    write(out_relpath, html)
    PAGES.append(out_relpath)


PAGES = []


def write_crawler_files():
    """Write sitemap.xml and robots.txt listing every rendered page."""
    base = SITE["url"]
    urls = "\n".join(f"  <url><loc>{base}{'' if p == 'index.html' else p}</loc></url>"
                     for p in PAGES)
    write("sitemap.xml",
          '<?xml version="1.0" encoding="UTF-8"?>\n'
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
          f"{urls}\n</urlset>\n")
    write("robots.txt", f"User-agent: *\nAllow: /\n\nSitemap: {base}sitemap.xml\n")


def main():
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT, exist_ok=True)

    news = load_news()
    members_data = load_members()
    stories = load_stories()
    ctx = dict(news=news, members_data=members_data, stories=stories)
    research_meta, _ = parse_frontmatter(os.path.join(CONTENT, "stories.md"))
    env.globals["latest_briefs"] = (research_meta.get("briefs") or [])[:3]

    # top-level pages
    for fn, out in [("home.md", "index.html"), ("about.md", "about.html"),
                    ("news.md", "news.html"), ("members.md", "members.html"),
                    ("stories.md", "stories.html"), ("join.md", "join.html")]:
        meta, body = parse_frontmatter(os.path.join(CONTENT, fn))
        render_page(meta, body, out, **ctx)

    # news posts
    for p in news:
        render_page(p, p["body"], p["url"], **ctx)

    # research stories
    for s in stories:
        render_page(s, s["body"], s["url"], **ctx)

    write_crawler_files()

    # static assets
    shutil.copytree(ASSETS, os.path.join(OUT, "assets"), dirs_exist_ok=True)
    print(f"\nBuilt site -> {OUT}  ({len(news)} news posts)")


if __name__ == "__main__":
    main()
