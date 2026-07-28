#!/usr/bin/env python3

import hashlib
import json
import re
import threading
import time

LIVE_PREFIX_RE = re.compile(
    r"""^\s*
    (?:
        EN\s+DIRECT
        |DIRECT
        |LIVE(?:\s+UPDATES?)?
        |BREAKING(?:\s+NEWS)?
        |JUST\s+IN
        |UPDATE
        |EN\s+IMAGES?
        |EN\s+VID[ÉE]O
    )
    \s*(?:[:;,.\-–—|]+\s*)?
    """,
    re.IGNORECASE | re.VERBOSE,
)


def clean_news_title(title):
    """Remove feed prefixes that waste space on the AWTRIX display."""
    title = re.sub(r"\s+", " ", str(title or "")).strip()

    previous = None
    while title and title != previous:
        previous = title
        title = LIVE_PREFIX_RE.sub("", title).strip()

    return title[:1].upper() + title[1:] if title else title

from datetime import datetime, timedelta, timezone
from pathlib import Path

import feedparser

from colors import COLORS
from display import clear, publish
from news_ranker import prioritize_items
from editor_v76 import edit_items_v76
from language_state import (
    cycle_output_language,
    language_label,
    load_output_language,
)
from feed_monitor import FeedHealth, check_feed, write_report


MAX_MESSAGES = 8
MAX_PER_FEED = 5

POLL_SECONDS = 300
BULLETIN_SECONDS = 10 * 60
NEWS_VISIBLE_SECONDS = 10 * 60
POOL_HOURS = 48

BASE_DIR = Path(__file__).resolve().parent
FEEDS_FILE = BASE_DIR / "feeds.json"
POOL_FILE = BASE_DIR / "cache/news_pool_v4.json"
LAST_BULLETIN_FILE = BASE_DIR / "cache/last_bulletin_v4.txt"
FORCE_REFRESH_FILE = Path("/tmp/vicky-news-force-refresh")
FEED_HEALTH_FILE = BASE_DIR / "cache/feed_health.json"
LOG_FILE = BASE_DIR / "logs/awtrix_news_vicki.log"


DEFAULT_FEEDS = [
    {
        "name": "france",
        "url": "https://www.lemonde.fr/rss/une.xml",
        "color": "france",
        "language": "fr",
        "priority": 10,
        "enabled": True,
    },
    {
        "name": "spiegel",
        "url": "https://www.spiegel.de/schlagzeilen/tops/index.rss",
        "color": "spiegel",
        "language": "de",
        "priority": 10,
        "enabled": True,
    },
    {
        "name": "bbc",
        "url": "https://feeds.bbci.co.uk/news/world/rss.xml",
        "color": "bbc",
        "language": "en",
        "priority": 8,
        "enabled": True,
    },
    {
        "name": "guardian",
        "url": "https://www.theguardian.com/world/rss",
        "color": "guardian",
        "language": "en",
        "priority": 8,
        "enabled": True,
    },
]


def log(message):
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    line = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {message}"
    print(line, flush=True)

    with LOG_FILE.open("a", encoding="utf-8") as file:
        file.write(line + "\n")


def normalize_title(title):
    title = title.lower()
    title = re.sub(r"[^\w\s]", " ", title, flags=re.UNICODE)
    title = re.sub(r"\s+", " ", title).strip()
    return title


def title_hash(title):
    normalized = normalize_title(title)
    return hashlib.sha1(normalized.encode("utf-8")).hexdigest()


def load_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)

    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary.replace(path)


def load_feeds():
    config = load_json(FEEDS_FILE, {"feeds": DEFAULT_FEEDS})
    feeds = config.get("feeds", [])
    valid = []

    for feed in feeds:
        if not isinstance(feed, dict):
            continue

        if not feed.get("enabled", True):
            continue

        name = str(feed.get("name", "")).strip()
        url = str(feed.get("url", "")).strip()

        if not name or not url:
            continue

        try:
            priority = int(feed.get("priority", 5))
        except (TypeError, ValueError):
            priority = 5

        valid.append(
            {
                "name": name,
                "url": url,
                "color": str(feed.get("color", "neutral")),
                "language": str(feed.get("language", "")),
                "priority": priority,
            }
        )

    return valid


def fetch_items():
    items = []
    health_results = []

    for feed in load_feeds():
        source = feed["name"]
        url = feed["url"]

        try:
            parsed = feedparser.parse(url)
            health = check_feed(
                feed,
                parser=lambda _url, result=parsed: result,
            )
            health_results.append(health)

            if not health.ok:
                log(f"feed SKIP {source}: {health.error}")
                continue

            if health.warning:
                log(f"feed warning {source}: {health.warning}")

            entries = parsed.entries[:MAX_PER_FEED]
            log(f"feed {source}: {len(entries)} titles")

            for entry in entries:
                title = clean_news_title(getattr(entry, "title", ""))
                if not title:
                    continue

                color = COLORS.get(
                    feed["color"],
                    COLORS.get("neutral", "CCCCCC"),
                )
                items.append(
                    {
                        "id": title_hash(title),
                        "source": source,
                        "source_code": str(
                            feed.get("code")
                            or source.upper()[:3]
                        ),
                        "title": title,
                        "color": color,
                        "language": feed["language"],
                        "priority": feed["priority"],
                        "first_seen": datetime.now().isoformat(timespec="seconds"),
                        "published": False,
                    }
                )

        except Exception as error:
            health_results.append(
                FeedHealth(
                    name=source,
                    url=url,
                    ok=False,
                    entries=0,
                    checked_at=datetime.now(timezone.utc).isoformat(
                        timespec="seconds"
                    ),
                    error=f"{type(error).__name__}: {error}",
                )
            )
            log(f"feed ERROR {source}: {error}")

    try:
        write_report(FEED_HEALTH_FILE, health_results)
        healthy = sum(result.ok for result in health_results)
        failed = len(health_results) - healthy
        log(f"feed health: {healthy} healthy, {failed} failed")
    except Exception as error:
        log(f"feed health report ERROR: {error}")

    return items

def load_pool():
    pool = load_json(POOL_FILE, [])

    if not isinstance(pool, list):
        return []

    return pool


def cleanup_pool(pool):
    cutoff = datetime.now() - timedelta(hours=POOL_HOURS)
    cleaned = []

    for item in pool:
        try:
            first_seen = datetime.fromisoformat(
                item["first_seen"]
            )
        except Exception:
            continue

        if (
            first_seen >= cutoff
            or not item.get("published", False)
        ):
            cleaned.append(item)

    return cleaned


def update_pool(new_items):
    pool = cleanup_pool(load_pool())
    known_ids = {item.get("id") for item in pool}
    added = 0

    for item in new_items:
        if item["id"] in known_ids:
            continue

        pool.append(item)
        known_ids.add(item["id"])
        added += 1

        log(
            f"POOL new: [{item['source']}] "
            f"{item['title']}"
        )

    save_json(POOL_FILE, pool)
    log(f"pool: {len(pool)} total, {added} added")
    return pool


def load_last_bulletin():
    try:
        return float(
            LAST_BULLETIN_FILE.read_text(
                encoding="utf-8"
            ).strip()
        )
    except Exception:
        return 0.0


def save_last_bulletin(timestamp):
    LAST_BULLETIN_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    LAST_BULLETIN_FILE.write_text(
        str(timestamp),
        encoding="utf-8",
    )


def bulletin_due():
    return (
        time.time() - load_last_bulletin()
        >= BULLETIN_SECONDS
    )


def color_for_message(message, items):
    message_headlines = message.get("headlines", [])

    for headline in message_headlines:
        for item in items:
            if item["title"] == headline:
                return item["color"]

    text = message.get("text", "")

    for item in items:
        if item["title"] == text:
            return item["color"]

        if item["title"] in text or text in item["title"]:
            return item["color"]

    return COLORS.get("neutral", "CCCCCC")


def source_code_for_message(message, items):
    """Return the source code belonging to the selected headline."""
    message_headlines = message.get("headlines", [])

    for headline in message_headlines:
        for item in items:
            if item.get("title") == headline:
                return str(
                    item.get("source_code")
                    or item.get("source", "RSS").upper()[:3]
                )

    text = str(message.get("text", "")).strip()

    for item in items:
        title = str(item.get("title", "")).strip()

        if not title:
            continue

        if title == text or title in text or text in title:
            return str(
                item.get("source_code")
                or item.get("source", "RSS").upper()[:3]
            )

    return "RSS"


def clear_news_topics():
    for index in range(1, 6):
        clear(f"vicky_news_a_{index}")
        clear(f"vicky_news_b_{index}")

    for index in range(1, 11):
        clear(f"vicky_news_{index}")
        clear(f"vicky_ai_news_{index}")

    log("news topics cleared")


def publish_news(messages, items):
    used = 0

    for index, message in enumerate(
        messages[:MAX_MESSAGES],
        start=1,
    ):
        text = str(message.get("text", "")).strip()

        if not text:
            continue

        if index <= 5:
            topic = f"vicky_news_a_{index}"
        else:
            topic = f"vicky_news_b_{index - 5}"

        color = color_for_message(message, items)
        source_code = source_code_for_message(message, items)
        display_text = f"{source_code}: {text}"

        publish(
            topic,
            display_text,
            color=color,
            repeat=2,
        )

        log(
            f"publish {topic}: "
            f"[importance "
            f"{message.get('importance', '?')}] "
            f"{display_text}"
        )

        used = index

    for index in range(used + 1, 6):
        clear(f"vicky_news_a_{index}")

    first_unused_b = max(1, used - 5 + 1)

    for index in range(first_unused_b, 6):
        clear(f"vicky_news_b_{index}")

    timer = threading.Timer(
        NEWS_VISIBLE_SECONDS,
        clear_news_topics,
    )
    timer.daemon = True
    timer.start()

    log(
        f"news will be cleared in "
        f"{NEWS_VISIBLE_SECONDS // 60} minutes"
    )


def mark_published(pool, messages):
    published_titles = set()

    for message in messages:
        for headline in message.get("headlines", []):
            published_titles.add(headline)

    now = datetime.now().isoformat(timespec="seconds")

    for item in pool:
        if item.get("title") in published_titles:
            item["published"] = True
            item["published_at"] = now

    save_json(POOL_FILE, pool)


def prepare_candidates(pool):
    candidates = [
        item
        for item in pool
        if not item.get("published", False)
    ]

    if not candidates:
        return []

    ranked = prioritize_items(candidates)

    ranked.sort(
        key=lambda item: int(
            item.get("priority", 5)
        ),
        reverse=True,
    )

    return ranked[:30]


def prepare_button_candidates(pool):
    """Return the five newest unique headlines, including previously shown ones."""
    newest_first = sorted(
        pool,
        key=lambda item: str(item.get("first_seen", "")),
        reverse=True,
    )

    result = []
    seen = set()

    for item in newest_first:
        title = str(item.get("title", "")).strip()
        key = normalize_title(title)

        if not title or not key or key in seen:
            continue

        seen.add(key)
        result.append(item)

        if len(result) >= 5:
            break

    return result


def create_button_bulletin(pool):
    """Publish five separate, safely translated headlines."""
    candidates = prepare_button_candidates(pool)

    log("---- VICKY V7.6 LLM BUTTON BULLETIN ----")
    log(f"button candidates: {len(candidates)}")

    if not candidates:
        log("no headlines available for button refresh")
        return False

    target_language = cycle_output_language()
    label = language_label(target_language)

    publish(
        "vicky_language",
        f"LANGUE: {label}",
        color="66CCFF",
        duration=5,
    )
    log(f"output language changed to {target_language}")

    time.sleep(5)
    clear("vicky_language")

    messages = edit_items_v76(
        candidates,
        maximum=5,
        target_language=target_language,
    )

    if not messages:
        log("safe editor returned no button messages")
        return False

    publish_news(messages, candidates)
    save_last_bulletin(time.time())

    log(f"button bulletin published: {len(messages)} messages")
    return True


def create_bulletin(pool):
    """Publish LLM-edited headlines with a safe offline fallback."""
    candidates = prepare_candidates(pool)

    # Möglichst unterschiedliche Quellen im selben Bulletin
    diversified = []
    seen_sources = set()

    for item in candidates:
        source = item.get("source", "")
        if source not in seen_sources:
            diversified.append(item)
            seen_sources.add(source)

    for item in candidates:
        if len(diversified) >= MAX_MESSAGES:
            break
        if item not in diversified:
            diversified.append(item)

    candidates = diversified

    log("---- VICKY VERSION 7.6 LLM BULLETIN ----")
    log(f"candidates: {len(candidates)}")

    if not candidates:
        log("no unpublished headlines")
        return False

    target_language = load_output_language()
    log(f"output language: {target_language}")

    messages = edit_items_v76(
        candidates,
        maximum=MAX_MESSAGES,
        target_language=target_language,
    )

    if not messages:
        log("safe editor returned no messages")
        return False

    log("safe editor result:")
    for message in messages:
        log(json.dumps(message, ensure_ascii=False))

    publish_news(messages, candidates)
    mark_published(pool, messages)
    save_last_bulletin(time.time())

    log(f"bulletin published: {len(messages)} messages")
    return True


def consume_button_request():
    if not FORCE_REFRESH_FILE.exists():
        return False

    try:
        FORCE_REFRESH_FILE.unlink()
    except FileNotFoundError:
        pass
    except PermissionError:
        log(
            "button request file could not be removed; "
            "continuing once"
        )

    return True


def run_once():
    feeds = load_feeds()
    log(f"V4 poll: {len(feeds)} enabled feeds")

    fetched = fetch_items()
    pool = update_pool(fetched)

    button_requested = consume_button_request()

    if button_requested:
        log("AWTRIX button refresh requested")
        clear_news_topics()
        create_button_bulletin(pool)

    elif bulletin_due():
        create_bulletin(pool)

    else:
        remaining = int(
            BULLETIN_SECONDS
            - (
                time.time()
                - load_last_bulletin()
            )
        )

        remaining = max(0, remaining)

        log(
            f"next bulletin in about "
            f"{remaining // 60} minutes"
        )


def main():
    log("VICKY Version 7.4 started")

    log(
        f"RSS poll every {POLL_SECONDS} seconds; "
        f"bulletin every "
        f"{BULLETIN_SECONDS // 60} minutes"
    )

    while True:
        try:
            run_once()
        except Exception as error:
            log(f"ERROR: {error}")

        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
