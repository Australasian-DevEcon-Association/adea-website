"""Parse the scraped members page into data/members.json and copy member photos
into assets/images/members/. Missing fields stay empty---never invented.

Three groups are preserved from the source page: leadership, members, PhD students.
Topic tags are canonicalized (synonyms collapsed) via TOPIC_CANON.

Schema (data/members.json):
{
  "leadership":    [ {name, role, topics[], countries[], link, photo} ],
  "members":       [ {name, institution, topics[], countries[], link, photo} ],
  "phd_students":  [ {name, institution, topics[], countries[], link, photo} ],
  "topics": [...], "countries": [...],
  "counts": {"leadership": N, "members": M, "phd_students": P}
}
"""
import os
import re
import csv
import json
from bs4 import BeautifulSoup
from PIL import Image, ImageOps

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRAPE = os.path.join(ROOT, "scrape")
SRC_HTML = os.path.join(SCRAPE, "html", "members.html")
SRC_IMG = os.path.join(SCRAPE, "images")
MANIFEST = os.path.join(SCRAPE, "image_manifest.csv")
ENRICH = os.path.join(ROOT, "data", "members_enrichment.json")
OUT_JSON = os.path.join(ROOT, "data", "members.json")
OUT_IMG = os.path.join(ROOT, "assets", "images", "members")
PHOTO_SHORT_EDGE = 600   # px; stored headshots keep their aspect, short edge capped here

ROLES = ["President", "Vice President", "Vice-President", "Secretary",
         "Treasurer", "Public Officer"]

# Collapse synonym/variant topic tags to a canonical label (lowercased key).
# Conservative: only clear synonyms, not distinct subfields.
TOPIC_CANON = {
    "agricultural": "Agriculture",
    "climate": "Climate Change",
    "development": "Development Economics",
    "gender studies": "Gender",
    "health economics": "Health",
    "health financing": "Health",
    "poverty reduction": "Poverty",
    "labor": "Labour Markets",
    "labour": "Labour Markets",
    "labor markets": "Labour Markets",
    "international migration": "Migration",
    "economics of immigration": "Migration",
    "economics of conflict": "Conflict",
    "empirical political economy": "Political Economy",
    "politics": "Political Economy",
    "environment": "Environmental Economics",
    "program evaluation": "Impact Evaluation",
    "social exclusion": "Social Inclusion",
    "energy economics": "Energy Economics",
}


def slugify(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def clean_link(href):
    """Drop placeholder/internal links (e.g. '/', '', ausdevea.org) so a card
    never renders a profile button that points back to the host site root."""
    href = (href or "").strip()
    if not href or href == "/" or href.startswith("/") or href.startswith("#"):
        return ""
    if "ausdevea" in href:
        return ""
    return href


def canon_topic(t):
    return TOPIC_CANON.get(t.lower(), t)


def split_list(s, canon=False):
    """Split a comma/semicolon/'and'-separated field into trimmed, de-duped items."""
    if not s:
        return []
    parts = re.split(r"[,;]|\band\b", s)
    out, seen = [], set()
    for p in parts:
        p = re.sub(r"\s+", " ", p).strip(" .;")
        if not p:
            continue
        if canon:
            p = canon_topic(p)
        if p.lower() not in seen:
            seen.add(p.lower())
            out.append(p)
    return out


def _between(text, start, end):
    m = re.search(start + r"\s*(.*?)\s*(?:" + end + r")", text, re.DOTALL | re.IGNORECASE)
    return m.group(1).strip() if m else ""


def load_photo_map():
    m = {}
    if not os.path.exists(MANIFEST):
        return m
    with open(MANIFEST, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["local_file"]:
                m[row["image_url"].split("?")[0]] = row["local_file"]
    return m


def copy_photo(data_image, slug, photo_map):
    if not data_image:
        return ""
    base = data_image.split("?")[0]
    local = photo_map.get(base)
    if not local or not os.path.exists(os.path.join(SRC_IMG, local)):
        return ""
    os.makedirs(OUT_IMG, exist_ok=True)
    im = ImageOps.exif_transpose(Image.open(os.path.join(SRC_IMG, local))).convert("RGB")
    # Keep the whole frame (no square pre-crop): the card crops in CSS with
    # object-fit/object-position, and members.json "photo_position" overrides per member.
    w, h = im.size
    scale = min(1.0, PHOTO_SHORT_EDGE / min(w, h))   # never upscale small originals
    if scale < 1.0:
        im = im.resize((round(w * scale), round(h * scale)), Image.LANCZOS)
    dst_name = slug + ".jpg"
    im.save(os.path.join(OUT_IMG, dst_name), "JPEG", quality=82, optimize=True, progressive=True)
    return f"members/{dst_name}"


def parse_member(li, group, photo_map):
    title = li.select_one(".list-item-content__title")
    desc = li.select_one(".list-item-content__description")
    link = li.select_one("a[href]")
    img = li.select_one("img")
    name = title.get_text(" ", strip=True) if title else ""
    body = desc.get_text(" ", strip=True) if desc else ""
    data_image = (img.get("data-image") or img.get("src")) if img else ""

    topics = split_list(_between(body, r"Areas of [Ii]nterest:", r"Countries:|$"), canon=True)
    countries = split_list(_between(body, r"Countries:", r"$"))
    prefix = re.split(r"Areas of [Ii]nterest:", body, flags=re.IGNORECASE)[0].strip()

    rec = {
        "name": name, "slug": slugify(name),
        "topics": topics, "countries": countries,
        "link": clean_link(link.get("href") if link else ""),
        "photo": copy_photo(data_image, slugify(name), photo_map),
        "group": group,
    }
    if group == "leadership":
        rec["role"] = next((r for r in ROLES if prefix.startswith(r)), "")
    else:
        rec["institution"] = prefix
    return rec


def apply_enrichment(rec):
    """Merge researched topics/countries for members whose ADEA entry had none.
    Only fills empty fields; records provenance. Never overwrites stated data."""
    if not os.path.exists(ENRICH):
        return rec
    data = json.load(open(ENRICH, encoding="utf-8"))
    e = data.get(rec["slug"])
    if not e:
        return rec
    if not rec["topics"] and e.get("topics"):
        rec["topics"] = [canon_topic(t) for t in e["topics"]]
        rec["topics_source"] = e.get("source", "")
    if not rec["countries"] and e.get("countries"):
        rec["countries"] = e["countries"]
    if not rec.get("link") and e.get("link"):
        rec["link"] = e["link"]
        rec["link_source"] = "researched"
    return rec


def main():
    soup = BeautifulSoup(open(SRC_HTML, encoding="utf-8").read(), "html.parser")
    photo_map = load_photo_map()
    lists = soup.select("ul.user-items-list-simple")
    # source page order: leadership, members, PhD students
    groups = ["leadership", "members", "phd_students"]
    bucket = {g: [] for g in groups}
    for idx, ul in enumerate(lists):
        group = groups[idx] if idx < len(groups) else "members"
        for li in ul.select(":scope > li"):
            rec = apply_enrichment(parse_member(li, group, photo_map))
            if rec["name"]:
                bucket[group].append(rec)

    everyone = bucket["leadership"] + bucket["members"] + bucket["phd_students"]

    def vocab(key):
        seen, out = {}, []
        for r in everyone:
            for v in r[key]:
                if v.lower() not in seen:
                    seen[v.lower()] = v
                    out.append(v)
        return sorted(out, key=str.lower)

    data = {
        "leadership": bucket["leadership"],
        "members": bucket["members"],
        "phd_students": bucket["phd_students"],
        "topics": vocab("topics"),
        "countries": vocab("countries"),
        "counts": {g: len(bucket[g]) for g in groups},
    }
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    no_topics = [r["name"] for r in everyone if not r["topics"]]
    with_photo = sum(1 for r in everyone if r["photo"])
    print(f"leadership {len(bucket['leadership'])}  members {len(bucket['members'])}  "
          f"phd {len(bucket['phd_students'])}")
    print(f"topics {len(data['topics'])}  countries {len(data['countries'])}  "
          f"photos {with_photo}/{len(everyone)}")
    print(f"still no topics ({len(no_topics)}): {no_topics}")
    print(f"-> {OUT_JSON}")


if __name__ == "__main__":
    main()
