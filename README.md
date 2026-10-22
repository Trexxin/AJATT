# AJATT

A question-answering system built on the archive of the All Japanese All The Time blog.
You ask a question about learning Japanese in English and get back an answer based on what
the blog actually says, with links to the posts it came from.

## Getting the data

The original site is down. There's a community-run copy of it at
<https://alljapanesealltheti.me/blog/>, which is served from the GitHub repo
[all-japanese-all-the-time/all-japanese-all-the-time](https://github.com/all-japanese-all-the-time/all-japanese-all-the-time).
The two scripts in `scraper/` grab the posts from there and turn them into JSON.

### Setup

```bash
pip install -r requirements.txt
```

### Step 1: collect the posts

```bash
python scraper/scrape.py --limit 20               # quick test, just grabs 20 posts
python scraper/scrape.py                          # crawl the whole site, about 25 minutes
python scraper/scrape.py --from-dir path/to/copy  # use a local copy of the site instead, under a minute
```

Both ways save each post to `data/raw/posts/<slug>.html`. Posts that are already saved get
skipped, so if a run gets interrupted you can just run it again. Only actual blog posts get
saved. Category, tag, series and archive pages are skipped, and so are the product and signup
pages the site has.

Crawling starts at the blog's front page and follows every link that stays under `/blog/`,
about 1,900 pages total, waiting half a second between requests. The local option works on
a folder that has one folder per page with an `index.html` inside, which is what you get from
cloning the GitHub repo above or saving the site.

### Step 2: parse them

```bash
python scraper/parse.py
```

Reads every file in `data/raw/posts/` and writes `data/processed/posts.jsonl`. Each line is
one post as JSON with these fields:

| Field | What it is |
|---|---|
| `slug` | The name of the post from its URL. |
| `url` | Link to the post on the site. |
| `title`, `author` | From the top of the post. `author` is empty for most of the tweet digests, since those pages don't have an author link. |
| `categories`, `series` | The categories and series the post is in. |
| `is_tweet_digest` | `true` for the weekly "AJATT Twitter Tweets" posts. There are about 230 of them. Kept in so they can be filtered out later. |
| `body` | The text of the post, one line per paragraph or list item. Stuff that WordPress plugins add inside the post, like series navigation, "related posts" lists and mailing list signup forms, is removed. Footnotes and image captions are kept. |
| `word_count` | Number of words in `body`. |
| `comments` | List of `{author, date, text}`. Pingbacks are left out. |
| `comment_count` | How many comments there are. |

There's no date on posts. The archived pages don't show when a post was published, only
when each comment was.
