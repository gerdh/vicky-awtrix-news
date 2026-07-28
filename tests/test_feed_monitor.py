from types import SimpleNamespace
import json

from feed_monitor import check_feed, check_feeds, write_report


def test_check_feed_success():
    def parser(url):
        assert url == "https://example.test/feed"
        return SimpleNamespace(entries=[{"title": "one"}, {"title": "two"}], bozo=False)

    result = check_feed(
        {"name": "Example", "url": "https://example.test/feed"},
        parser=parser,
    )

    assert result.ok is True
    assert result.entries == 2
    assert result.error == ""


def test_check_feed_empty_is_failure():
    result = check_feed(
        {"name": "Empty", "url": "https://example.test/empty"},
        parser=lambda url: SimpleNamespace(entries=[], bozo=False),
    )

    assert result.ok is False
    assert result.error == "feed returned no entries"


def test_check_feed_parser_error_is_isolated():
    def broken_parser(url):
        raise RuntimeError("network down")

    result = check_feed(
        {"name": "Broken", "url": "https://example.test/broken"},
        parser=broken_parser,
    )

    assert result.ok is False
    assert "RuntimeError: network down" == result.error


def test_disabled_feeds_are_skipped():
    results = check_feeds(
        [
            {"name": "Disabled", "url": "https://example.test/a", "enabled": False},
            {"name": "Enabled", "url": "https://example.test/b", "enabled": True},
        ],
        parser=lambda url: SimpleNamespace(entries=[1], bozo=False),
    )

    assert [result.name for result in results] == ["Enabled"]


def test_write_report_creates_summary(tmp_path):
    results = [
        check_feed(
            {"name": "Good", "url": "https://example.test/good"},
            parser=lambda url: SimpleNamespace(entries=[1], bozo=False),
        ),
        check_feed(
            {"name": "Bad", "url": "https://example.test/bad"},
            parser=lambda url: SimpleNamespace(entries=[], bozo=False),
        ),
    ]

    target = tmp_path / "feed_health.json"
    write_report(target, results)
    payload = json.loads(target.read_text(encoding="utf-8"))

    assert payload["summary"]["total"] == 2
    assert payload["summary"]["ok"] == 1
    assert payload["summary"]["failed"] == 1
