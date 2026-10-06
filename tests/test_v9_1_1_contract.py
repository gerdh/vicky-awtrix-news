import json
from pathlib import Path

import awtrix_news_vicki as news


ROOT = Path(__file__).resolve().parents[1]


def test_requested_german_sources_are_enabled_without_language_quota():
    feeds = json.loads((ROOT / "feeds.json").read_text(encoding="utf-8"))["feeds"]
    by_name = {feed["name"]: feed for feed in feeds}

    assert by_name["faz"]["code"] == "FAZ"
    assert by_name["sueddeutsche"]["code"] == "SZ"
    assert by_name["abendzeitung_muenchen"]["code"] == "AZ"
    assert all(
        by_name[name]["language"] == "de" and by_name[name]["enabled"]
        for name in ("faz", "sueddeutsche", "abendzeitung_muenchen")
    )


def test_feed_loader_preserves_configured_source_codes(tmp_path, monkeypatch):
    config = {
        "feeds": [
            {
                "name": "sueddeutsche",
                "url": "https://rss.sueddeutsche.de/rss/Topthemen",
                "color": "neutral",
                "language": "de",
                "priority": 10,
                "enabled": True,
                "code": "SZ",
            }
        ]
    }
    feeds_file = tmp_path / "feeds.json"
    feeds_file.write_text(json.dumps(config), encoding="utf-8")
    monkeypatch.setattr(news, "FEEDS_FILE", feeds_file)

    assert news.load_feeds()[0]["code"] == "SZ"


def test_button_contract_keeps_right_language_and_left_refresh():
    script = (ROOT / "scripts/vicky-awtrix-button").read_text(encoding="utf-8")
    left_block, right_block = script.split('"$AWTRIX_UID/stats/buttonRight")', 1)

    assert "cycle_output_language" not in left_block
    assert "touch /tmp/vicky-news-force-refresh" in left_block
    assert "cycle_output_language" in right_block
    assert "touch /tmp/vicky-news-force-refresh" in right_block
    assert "/home/gerd/vicky8" not in script
    assert 'CONFIG_BASE_TOPIC%/custom' in script


def test_button_refresh_wakes_news_loop_without_five_minute_delay(tmp_path, monkeypatch):
    request_file = tmp_path / "refresh"
    request_file.touch()
    monkeypatch.setattr(news, "FORCE_REFRESH_FILE", request_file)

    assert news.wait_for_refresh(timeout=0.1, interval=0.01) is True


def test_release_version_is_9_1_1():
    assert (ROOT / "VERSION").read_text(encoding="utf-8").strip() == "9.1.1"
