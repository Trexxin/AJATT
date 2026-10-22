"""Collect the HTML of every AJATT blog post, from the hosted archive mirror or a local copy.

Usage (run from the repo root):
    python scraper/scrape.py                     crawl the mirror, took around 25 minutes
    python scraper/scrape.py --limit 20          stop after saving 20 posts, for testing
    python scraper/scrape.py --from-dir PATH     read a local copy of the archive instead, under a minute

Either way, posts get put in data/raw/posts/<slug>.html. If you interrupted the run for whatever reason, just run it
again. Posts that were already saved get skipped.
"""

import argparse
import os
import time
from urllib.parse import unquote, urldefrag, urljoin

import requests
from bs4 import BeautifulSoup

from parse import is_post_page

START_URL = "https://alljapanesealltheti.me/blog/"
RAW_DIR = os.path.join("data", "raw", "posts")
DELAY_SECONDS = 0.5
HEADERS = {"User-Agent": "AJATT-QA-scraper"}


def normalize_url(page_url, href):
    """Turn a link from a page into a full URL we want to crawl, or None if we should skip it.

    We skip links that go outside the blog, links to files like images and zips,
    and links with a ? in them. Also, ".../some-post/" and ".../some-post/index.html"
    are the same page on this site, so both get turned into ".../some-post/" so we
    don't visit it twice.
    """
    url, _fragment = urldefrag(urljoin(page_url, href))
    if "?" in url or not url.startswith(START_URL):
        return None
    if url.endswith("/index.html"):
        url = url[: -len("index.html")]
    last_part = url.rstrip("/").split("/")[-1]
    if "." in last_part:
        return None
    if not url.endswith("/"):
        url += "/"
    return url


def slug_from_url(url):
    """Get the post's slug from its URL, e.g. .../blog/some-post/ -> some-post.

    Some URLs have Japanese in them, which shows up encoded like %e3%81%a9.
    unquote() turns that back into the real characters so the file name ends up
    the same as the folder name in a local copy of the archive.
    """
    return unquote(url[len(START_URL):]).strip("/").replace("/", "__")


def save_post(slug, html):
    """Save one post's HTML to RAW_DIR. Returns False if we already have that post."""
    path = os.path.join(RAW_DIR, slug + ".html")
    if os.path.exists(path):
        return False
    with open(path, "w", encoding="utf-8") as file:
        file.write(html)
    return True


def collect_from_dir(source_dir, limit):
    """Go through a local copy of the archive and save every post in it. Returns how many were new.

    The local copy has one folder per page with an index.html inside, same as the
    site. The folder name is used as the slug, so the files come out named the same
    as they would from crawling.
    """
    saved = 0
    for folder, subfolders, files in os.walk(source_dir):
        subfolders[:] = [name for name in subfolders if name != ".git"]
        if "index.html" not in files:
            continue
        with open(os.path.join(folder, "index.html"), encoding="utf-8", errors="replace") as file:
            html = file.read()
        if not is_post_page(BeautifulSoup(html, "html.parser")):
            continue
        if save_post(os.path.basename(folder), html):
            saved += 1
            if limit and saved >= limit:
                break
    return saved


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--limit", type=int, default=0,
                        help="stop after saving this many new posts (0 = no limit)")
    parser.add_argument("--from-dir", metavar="PATH",
                        help="read a local copy of the archive instead of crawling the mirror")
    args = parser.parse_args()

    os.makedirs(RAW_DIR, exist_ok=True)

    if args.from_dir:
        saved = collect_from_dir(args.from_dir, args.limit)
        print(f"done: saved {saved} new posts from {args.from_dir} to {RAW_DIR}")
        return

    to_visit = [START_URL]
    visited = set()
    saved = 0

    while to_visit:
        url = to_visit.pop(0)
        if url in visited:
            continue
        visited.add(url)

        try:
            response = requests.get(url, headers=HEADERS, timeout=30)
        except requests.RequestException as error:
            print("failed:", url, error)
            continue
        if response.status_code != 200 or "text/html" not in response.headers.get("Content-Type", ""):
            continue

        soup = BeautifulSoup(response.text, "html.parser")

        if is_post_page(soup) and save_post(slug_from_url(url), response.text):
            saved += 1
            print(f"[{saved}] saved {url}")
            if args.limit and saved >= args.limit:
                break

        for link in soup.find_all("a", href=True):
            next_url = normalize_url(url, link["href"])
            if next_url and next_url not in visited:
                to_visit.append(next_url)

        time.sleep(DELAY_SECONDS)

    print(f"done: visited {len(visited)} pages, saved {saved} new posts to {RAW_DIR}")


if __name__ == "__main__":
    main()
