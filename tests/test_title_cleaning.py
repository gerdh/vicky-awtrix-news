from awtrix_news_vicki import clean_news_title


def test_removes_french_live_prefix():
    assert (
        clean_news_title(
            "EN DIRECT, incendies : importante reprise de feu"
        )
        == "Incendies : importante reprise de feu"
    )


def test_removes_live_updates_prefix():
    assert (
        clean_news_title("LIVE UPDATES: Major storm approaches")
        == "Major storm approaches"
    )


def test_removes_breaking_prefix():
    assert (
        clean_news_title("BREAKING: Government announces changes")
        == "Government announces changes"
    )


def test_removes_just_in_prefix():
    assert (
        clean_news_title("JUST IN – New technology unveiled")
        == "New technology unveiled"
    )


def test_preserves_normal_title():
    title = "Séisme au Japon : une alerte tsunami déclenchée"
    assert clean_news_title(title) == title
