from offline_translator import _unsafe_translation, translate_title


def test_french_title_is_unchanged():
    title = "Incendies en France"
    assert translate_title(title, "fr") == title


def test_unknown_language_falls_back_to_original():
    title = "Notizia internazionale"
    assert translate_title(title, "it") == title


def test_empty_title_stays_empty():
    assert translate_title("", "de") == ""


def test_repetitive_translation_is_rejected():
    repeated = "feu en Espagne " * 20
    assert _unsafe_translation("Waldbrand in Spanien", repeated)
