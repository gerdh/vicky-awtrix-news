from unittest.mock import patch

from safe_news_editor import edit_items_safely


def test_one_message_per_original_title():
    items = [
        {
            "source": "spiegel",
            "title": "Deutscher Titel",
            "language": "de",
            "priority": 8,
        },
        {
            "source": "bbc",
            "title": "English title",
            "language": "en",
            "priority": 9,
        },
    ]

    with patch(
        "safe_news_editor.translate_title",
        side_effect=["Titre allemand", "Titre anglais"],
    ):
        messages = edit_items_safely(items, maximum=5)

    assert len(messages) == 2
    assert messages[0]["headlines"] == ["Deutscher Titel"]
    assert messages[1]["headlines"] == ["English title"]
    assert messages[0]["importance"] == 8
    assert messages[1]["importance"] == 9


def test_message_limit_is_respected():
    items = [
        {
            "source": "test",
            "title": f"Title {index}",
            "language": "fr",
            "priority": 5,
        }
        for index in range(10)
    ]

    messages = edit_items_safely(items, maximum=5)
    assert len(messages) == 5
