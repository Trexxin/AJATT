"""Turn the saved post HTML files into one JSON object per post.

Usage (run from the repo root):
    python scraper/parse.py                       reads data/raw/posts, writes data/processed/posts.jsonl
    python scraper/parse.py --raw-dir X --out Y   if the files are somewhere else

Each line of the output file is one post as JSON with these fields:
    slug, url, title, author, categories, series, is_tweet_digest,
    body, word_count, comments (list of {author, date, text}), comment_count

There is no date field for the post itself. The archived pages don't show when a
post was published (for some reason), only when each comment was.
"""

import argparse
import glob
import json
import os

from bs4 import BeautifulSoup

RAW_DIR = os.path.join("data", "raw", "posts")
OUT_PATH = os.path.join("data", "processed", "posts.jsonl")
SITE = "https://alljapanesealltheti.me/blog/"


def clean_text(tag):
    """Get the text inside a tag as one line with normal spacing. Gives "" if the tag is None."""
    if tag is None:
        return ""
    return " ".join(tag.get_text(" ").split())


def block_text(tag):
    """Get the text inside a tag, one line per paragraph or list item, no blank lines."""
    lines = [" ".join(line.split()) for line in tag.get_text("\n").split("\n")]
    return "\n".join(line for line in lines if line)


def is_post_page(soup):
    """Check if a page is an actual blog post.

    Two kinds of pages look like posts but aren't, so we check two things:
    - Category, author and year archive pages show full posts inside <article>
      tags too. Only a real post page has "single-post" in the <body> class.
    - Product, signup and billing pages use the same template as posts, but
      their <article> is missing the "type-post" class.
    """
    body = soup.find("body")
    article = soup.find("article")
    return (body is not None
            and "single-post" in body.get("class", [])
            and article is not None
            and "type-post" in article.get("class", [])
            and article.find(class_="entry-content") is not None)


def parse_post(html, slug):
    """Pull everything we want out of one post's HTML into a dict. Returns None if it isn't a post."""
    soup = BeautifulSoup(html, "html.parser")
    if not is_post_page(soup):
        return None
    article = soup.find("article")
    content = article.find(class_="entry-content")

    # WordPress plugins stick extra stuff inside the post body that isn't part of the
    # post: the "This entry is part N of M in the series" line, the list of other
    # posts in the series, and two different "related posts" boxes. We just get rid of all of i.
    # There MIGHT be some entries left over but from what I combed over I beleive most of them are 
    # accounted for.
    for box in content.find_all(class_=["seriesmeta", "seriesbox", "rp4wp-related-posts",
                                        "zemanta-related-title", "zemanta-article-ul"]):
        box.decompose()
    # Some posts have a mailing list signup form in the middle of them.
    for form in content.find_all("form"):
        form.decompose()
    # The "Series Navigation" box is a <fieldset> with that as its <legend>.
    for box in content.find_all("fieldset"):
        if box.legend is not None and "Series Navigation" in box.legend.get_text():
            box.decompose()

    classes = article.get("class", [])
    author_link = article.find("a", rel="author")

    comments = []
    for item in soup.find_all("li", class_="comment"):
        text_tag = item.find(class_="comment-text")
        if text_tag is None:
            continue  # no text in this comment, skip it instead of crashing
        comments.append({
            "author": clean_text(item.find(class_="comment-author")),
            "date": clean_text(item.find(class_="comment-meta")),
            "text": block_text(text_tag),
        })

    body = block_text(content)
    return {
        "slug": slug,
        "url": SITE + slug.replace("__", "/") + "/",
        "title": clean_text(article.find(class_="entry-title")),
        "author": clean_text(author_link),
        "categories": [c[len("category-"):] for c in classes if c.startswith("category-")],
        "series": [c[len("series-"):] for c in classes if c.startswith("series-")],
        "is_tweet_digest": slug.startswith("ajatt-twitter-tweets"),
        "body": body,
        "word_count": len(body.split()),
        "comments": comments,
        "comment_count": len(comments),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--raw-dir", default=RAW_DIR)
    parser.add_argument("--out", default=OUT_PATH)
    args = parser.parse_args()

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    paths = sorted(glob.glob(os.path.join(args.raw_dir, "*.html")))
    written = 0
    skipped = 0

    with open(args.out, "w", encoding="utf-8") as out:
        for path in paths:
            slug = os.path.splitext(os.path.basename(path))[0]
            # One of the archived pages has some bad bytes in it that aren't valid
            # UTF-8. errors="replace" swaps those for a placeholder character instead
            # of crashing the whole run.
            with open(path, encoding="utf-8", errors="replace") as file:
                post = parse_post(file.read(), slug)
            if post is None:
                skipped += 1
                continue
            out.write(json.dumps(post, ensure_ascii=False) + "\n")
            written += 1

    print(f"wrote {written} posts to {args.out} ({skipped} files skipped as non-posts)")


if __name__ == "__main__":
    main()
