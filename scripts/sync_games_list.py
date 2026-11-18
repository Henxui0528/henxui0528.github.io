#!/usr/bin/env python3
"""Build games.json (the "More games by Henxui" list read by every game) from
the public Google Play developer page, so a newly published game appears in
all released games without rebuilding any of them.

  python3 scripts/sync_games_list.py [--out games.json] [--dev-id N]

Only games that are really published show up on the developer page. Names,
one-line descriptions and icons come from each game's own store listing (vi
and en). Nothing is written when the page cannot be read or lists no game, so
a Play outage never empties the list. Run it by hand after a release, or on a
schedule from the site repo (see docs/RELEASE_GUIDE.md section 1.9).
"""
import argparse
import html
import json
import re
import sys
import urllib.request

DEV_ID = "5368551620364828884"
UA = "Mozilla/5.0 (compatible; HenxuiGamesList/1.0)"


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def app_ids(dev_page):
    seen = []
    for m in re.finditer(r"details\?id=([A-Za-z][A-Za-z0-9_.]*)", dev_page):
        if m.group(1) not in seen:
            seen.append(m.group(1))
    return seen


def meta(page, prop):
    m = re.search(r'<meta[^>]*property="%s"[^>]*content="([^"]*)"' % prop, page)
    return html.unescape(m.group(1)).strip() if m else ""


def listing(app_id, lang):
    page = fetch(f"https://play.google.com/store/apps/details?id={app_id}&hl={lang}")
    title = meta(page, "og:title").rsplit(" - ", 1)[0].strip()
    icon = re.sub(r"=s\d+-.*$|=s\d+$", "", meta(page, "og:image"))
    return title, meta(page, "og:description"), icon


def build(dev_id):
    ids = app_ids(fetch(f"https://play.google.com/store/apps/dev?id={dev_id}&hl=en"))
    games = []
    for app_id in ids:
        vi_name, vi_tag, icon = listing(app_id, "vi")
        en_name, en_tag, _ = listing(app_id, "en")
        if not (vi_name or en_name):
            continue
        games.append({
            "id": app_id,
            "name": {"vi": vi_name or en_name, "en": en_name or vi_name},
            "tagline": {"vi": vi_tag, "en": en_tag},
            "icon": icon + "=s256" if icon.startswith("https://") else "",
        })
    return {"games": games}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="games.json")
    ap.add_argument("--dev-id", default=DEV_ID)
    a = ap.parse_args()
    try:
        data = build(a.dev_id)
    except Exception as e:  # network, layout change...
        print(f"cannot read Google Play: {e}", file=sys.stderr)
        return 1
    if not data["games"]:
        print("no games found; keeping the current file", file=sys.stderr)
        return 1
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print("games:", ", ".join(g["id"] for g in data["games"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
