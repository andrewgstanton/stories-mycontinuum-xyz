import os
import sys
import json
import pytz
import uuid
import markdown
import asyncio
import websockets

from utils import decode_npub, generate_link, shorten_url
from datetime import datetime
from slugify import slugify
from pathlib import Path

# set time zone
pst = pytz.timezone("US/Pacific")

OUTPUT_DIR = "docs/articles"

print("Current working dir:", os.getcwd())
print("Articles will be saved to:", os.path.join(os.getcwd(), OUTPUT_DIR))

os.makedirs(OUTPUT_DIR, exist_ok=True)

input_key = os.getenv("PUBKEY", "").strip()

if not input_key:
    print("Error: PUBKEY environment variable is required.", file=sys.stderr)
    sys.exit(1)

print("Current PUBKEY", input_key)

try:
    pubkey_hex = decode_npub(input_key) if input_key.startswith("npub") else input_key
except Exception as e:
    print(f"Invalid PUBKEY: {e}", file=sys.stderr)
    sys.exit(1)

print("Current PUBKEY (hex):", pubkey_hex)

RELAY_URLS = [
    "wss://relay.primal.net",
    "wss://relay.damus.io",
    "wss://nos.lol",
    "wss://relay.snort.social",
    "wss://purplepag.es",
    "wss://premium.primal.net",
    "wss://nostr.mom",
    "wss://relay.nostr.band",
    "wss://nostr.at"
]


async def fetch_from_relay(url, pubkey_hex):
    articles = []
    try:
        print("fetching from relay:", url)
        async with websockets.connect(url) as ws:
            sub_id = str(uuid.uuid4())
            await ws.send(json.dumps([
                "REQ",
                sub_id,
                {
                    "kinds": [30023],
                    "authors": [pubkey_hex]
                }
            ]))

            while True:
                try:
                    msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=5))
                    if msg[0] == "EVENT" and msg[1] == sub_id:
                        articles.append(msg[2])
                    elif msg[0] == "EOSE":
                        break
                except asyncio.TimeoutError:
                    break
    except Exception as e:
        print(f"[{url}] Failed: {e}")

    return articles


def has_continuum_stories_tag(event):
    tags = event.get("tags", [])
    return any(tag[0] == "t" and tag[1] == "continuum-stories" for tag in tags)


def extract_article_data(event):
    tags = {tag[0]: tag[1] for tag in event.get("tags", []) if len(tag) > 1}
    taglist = [tag[1].lower() for tag in event.get("tags", []) if tag[0] == "t"]

    title = tags.get("title")
    if not title:
        print(f"Skipping event {event.get('id', 'UNKNOWN')} — no title tag")
        return None

    slug = slugify(title)
    summary = tags.get("summary", "")
    image_url = tags.get("image", "")

    content = markdown.markdown(
        event["content"].replace("\\n", "\n").replace("\\", ""),
        extensions=["extra"]
    )

    dt = datetime.fromtimestamp(event.get("created_at")).strftime("%Y-%m-%d")
    published_at_ts = int(tags.get("published_at", event.get("created_at")))
    created_at_ts = event.get("created_at")

    published_date = datetime.fromtimestamp(
        published_at_ts, tz=pst
    ).strftime("%B %d, %Y at %I:%M %p %Z")

    updated_date = datetime.fromtimestamp(
        created_at_ts, tz=pst
    ).strftime("%B %d, %Y at %I:%M %p %Z")

    event_id = event.get("id")

    raw_url = generate_link(event_id)
    original_url = shorten_url(raw_url)

    return {
        "title": title,
        "slug": slug,
        "summary": summary,
        "image": image_url,
        "tags": taglist,
        "content": content,
        "date": dt,
        "timestamp": created_at_ts,
        "published_at": published_at_ts,
        "published_date": published_date,
        "updated_date": updated_date,
        "event_id": event_id,
        "original_url": original_url
    }


def build_tags_html(tags):
    if not tags:
        return ""

    return (
        '<div class="article-tags">'
        + "".join(f'<span class="tag">#{tag}</span>' for tag in tags)
        + "</div>"
    )


def build_hero_image_html(image_url):
    if not image_url:
        return ""

    return f"""
    <img
      class="article-hero-image"
      src="{image_url}"
      alt="Hero image"
    >
    """


def build_summary_html(summary):
    if not summary:
        return ""

    return f"""
    <p class="article-summary">
      <strong>{summary}</strong>
    </p>
    """


def render_article_html(article):
    tags_html = build_tags_html(article["tags"])
    hero_image_html = build_hero_image_html(article["image"])
    summary_html = build_summary_html(article["summary"])

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{article["title"]}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">

<link rel="stylesheet" href="https://mycontinuum.xyz/styles/style.css">
<style>
  .article-page {{
    max-width: 860px;
  }}

  .article-meta {{
    color: #666;
    font-size: 0.95rem;
    margin-top: 0.5rem;
  }}

  .article-summary {{
    font-size: 1.05rem;
    line-height: 1.7;
    margin-top: 1rem;
    margin-bottom: 1.5rem;
  }}

  .article-hero-image {{
    max-width: 100%;
    height: auto;
    margin: 1.5rem 0;
    display: block;
  }}

  .article-content {{
    margin-top: 1.5rem;
  }}

  .article-content img {{
    max-width: 100%;
    height: auto;
  }}

  .article-content .tags,
  .article-tags {{
    margin: 1.25rem 0;
  }}

  .article-content .tag,
  .article-tags .tag {{
    display: inline-block;
    margin: 0 0.4rem 0.4rem 0;
    padding: 0.2rem 0.5rem;
    border: 1px solid #ddd;
    border-radius: 999px;
    font-size: 0.9rem;
    color: #444;
  }}

  .original-link-block {{
    font-size: 0.9rem;
    color: #666;
    margin-top: 2rem;
  }}

  .original-link-block a {{
    word-break: break-word;
  }}
</style>
</head>

<body>

<div class="page-shell">

  <div class="nav">
    <a href="https://mycontinuum.xyz/">Home</a>
    <a href="https://mycontinuum.xyz/overview.html">Overview</a>
    <a href="https://drive.google.com/file/d/1jzIAHwQc6JCvgPj7anyAwA3uFARqyJ7-/view?usp=drive_link" target="_blank" rel="noopener noreferrer">Demo</a>
    <a href="https://mycontinuum.xyz/downloads.html">Downloads</a>
    <a href="https://mycontinuum.xyz/pricing.html">Pricing</a>
    <a href="https://mycontinuum.xyz/use_cases.html">Who Continuum Is For</a>
    <a href="https://mycontinuum.xyz/faqs.html">FAQs</a>
    <a href="https://mycontinuum.xyz/books.html">Books</a>
    <a href="https://mycontinuum.xyz/open_source.html">Open Source</a>            
    <a href="https://stories.mycontinuum.xyz/">Stories</a>
  </div>

  <div class="hero article-page">
    <p><a href="https://stories.mycontinuum.xyz/">← Back to Stories</a></p>

    <h1>{article["title"]}</h1>

    <p class="article-meta">
      Published: {article["published_date"]}
      &nbsp; | &nbsp;
      Updated: {article["updated_date"]}
    </p>

    {hero_image_html}

    {summary_html}

    {tags_html}
  </div>

  <hr>

  <div class="section article-page">
    <div class="article-content">
      {article["content"]}

      <div class="original-link-block">
        Original post:
        <a href="{article["original_url"]}" target="_blank" rel="noopener noreferrer">
          {article["original_url"]}
        </a>
      </div>
    </div>
  </div>

  <hr>

  <footer>
    <p>© 2025–2026 Andrew G. Stanton.</p>
    <p>Continuum software and documentation.</p>

    <p>
      Powered by
      <a href="https://nostr.com" target="_blank" rel="noopener noreferrer">Nostr</a>
      +
      <a href="https://github.com/features/actions" target="_blank" rel="noopener noreferrer">GitHub Actions</a>.
    </p>
    <p>
      Content licensed under
      <a href="https://creativecommons.org/licenses/by/4.0/" target="_blank" rel="noopener noreferrer">CC BY 4.0</a>.
    </p>
  </footer>

</div>

</body>
</html>
"""


def write_articles(articles):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    index = []

    for article in articles:
        path = Path(OUTPUT_DIR) / article["slug"]
        path.mkdir(parents=True, exist_ok=True)

        html = render_article_html(article)

        with open(path / "index.html", "w", encoding="utf-8") as f:
            f.write(html)

        index.append({
            "title": article["title"],
            "slug": article["slug"],
            "date": article["published_date"],
            "original_url": article["original_url"]
        })

    with open(Path(OUTPUT_DIR) / "index.json", "w", encoding="utf-8") as f:
        json.dump(index[:10], f, indent=2)


async def fetch_all_articles():
    tasks = [fetch_from_relay(url, pubkey_hex) for url in RELAY_URLS]
    results = await asyncio.gather(*tasks)
    all_articles = [item for sublist in results for item in sublist]
    print(f"Fetched {len(all_articles)} total articles (including duplicates)")

    unique_articles = {}
    for article in all_articles:
        unique_articles[article["id"]] = article

    deduped_articles = list(unique_articles.values())
    print(f"After deduplication: {len(deduped_articles)} unique articles")

    filtered_articles = [ev for ev in deduped_articles if has_continuum_stories_tag(ev)]
    print(f"Filtered down to {len(filtered_articles)} articles tagged with 'continuum-stories'")

    return filtered_articles


if __name__ == "__main__":
    articles_raw = asyncio.run(fetch_all_articles())

    articles = []
    for event in articles_raw:
        try:
            a = extract_article_data(event)
            if a:
                articles.append(a)
        except Exception as e:
            print(f"Error processing article: {e}")

    articles = sorted(articles, key=lambda x: x["published_at"], reverse=True)[:10]
    write_articles(articles)