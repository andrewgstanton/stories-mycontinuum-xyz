import os
import json
import pytz
import time
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
print("Articles will be saved to:", os.path.join(os.getcwd(), "docs/articles"))

os.makedirs("articles", exist_ok=True)

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
        print("feching from relay:", url)
        async with websockets.connect(url) as ws:
            sub_id = str(uuid.uuid4())
            await ws.send(json.dumps(["REQ", sub_id, {
                "kinds": [30023],
                "authors": [pubkey_hex]
            }]))
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

# Filter by tag: only keep if tag "t" has "blog" or "article"
def has_continuum_stories_tag(event):
    tags = event.get("tags", [])
    return any(tag[0] == "t" and tag[1] == "continuum-stories" for tag in tags)

def extract_article_data(event):
    # print("=== RAW EVENT ===")
    # print(json.dumps(event, indent=2))  # event is a dict

    tags = {tag[0]: tag[1] for tag in event.get("tags", []) if len(tag) > 1}
    taglist = [tag[1].lower() for tag in event.get("tags", []) if tag[0] == "t"]

    title = tags.get("title")
    if not title:
        print(f"Skipping event {event.get('id', 'UNKNOWN')} — no title tag")
        return None

    slug = slugify(title)
    summary = tags.get("summary", "")
    image_url = tags.get("image", "")
    content = markdown.markdown(event["content"].replace("\\n", "\n").replace("\\", ""))
    dt = datetime.fromtimestamp(event.get("created_at")).strftime("%Y-%m-%d")
    published_at_ts = int(tags.get("published_at", event.get("created_at")))
    created_at_ts = event.get("created_at")
    published_date = datetime.fromtimestamp(published_at_ts, tz=pst).strftime("%B %d, %Y at %I:%M %p %Z")
    updated_date = datetime.fromtimestamp(created_at_ts, tz=pst).strftime("%B %d, %Y at %I:%M %p %Z")
    event_id = event.get("id")

    # Use helper to generate and shorten original_url
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

def write_articles(articles):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    index = []

    for article in articles:
        path = Path(OUTPUT_DIR) / article["slug"]
        path.mkdir(parents=True, exist_ok=True)

        tags_html = (
            "<div class='tags'>"
            + "".join(f"<span class='tag'>#{tag}</span>" for tag in article["tags"])
            + "</div>"
            if article["tags"] else ""
        )

        hero_image_html = (
            f"<img src='{article['image']}' alt='Hero image' style='max-width: 100%; margin-bottom: 20px;'/>"
            if article["image"] else ""
        )

        summary_html = f"<p><strong>{article['summary']}</strong></p>" if article["summary"] else ""

        html = f"""<html><body>
                    <!DOCTYPE html>
                    <html lang="en">
                    <head>
                        <meta charset="UTF-8" />
                        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
                        <title>Continuum - Stories</title>
                        <link rel="stylesheet" href="../../styles/styles.css" />
                    </head>
                    <body>
                        <h2><div class="site-title">Continuum - Stories</div></h2>
                        <div class="site-subtitle">Decentralized.  Sovereign. Free. </div>
                <div class="container">
        <h1>{article['title']}</h1>
        <p><em>Published: {article['published_date']} &nbsp; | &nbsp; Updated: {article['updated_date']}</em></p>
        {hero_image_html}
        {summary_html}
        {tags_html}
        {article['content']}
        <p style="font-size: 0.8em; color: #777;">
            Original post: <a href="{article['original_url']}" target="_blank">{article['original_url']}</a>
        </p>

        <footer>
            <p style="font-size: 0.85em; color: #777;">
            Powered by <a href="https://nostr.com" target="_blank">Nostr</a> + <a href="https://github.com/features/actions" target="_blank">GitHub Actions</a><br/>
            Content licensed under <a href="https://creativecommons.org/licenses/by/4.0/" target="_blank">CC BY 4.0</a> <br> <br/>
                © 2025-2026 - Continuum. All rights reserved. 
            </br></p>
        </footer>
        
        </div>
        </body></html>"""

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

    # Deduplicate using event ID
    unique_articles = {}
    for article in all_articles:
        unique_articles[article['id']] = article  # overwrite dupes

    deduped_articles = list(unique_articles.values())
    print(f"After deduplication: {len(deduped_articles)} unique articles")

    filtered_articles = [ev for ev in deduped_articles if has_continuum_stories_tag(ev)]
    print(f"Filtered down to {len(filtered_articles)} articles tagged with 'blog' or 'article'")

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
