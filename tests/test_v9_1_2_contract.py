from pathlib import Path

import awtrix_news_vicki as news


ROOT = Path(__file__).resolve().parents[1]


def _item(source, title, first_seen):
    return {
        "source": source,
        "title": title,
        "first_seen": first_seen,
    }


def test_button_candidates_prefer_distinct_sources_before_backfill():
    pool = [
        _item("lesechos", "ECO 5", "2026-10-07T11:31:15"),
        _item("lesechos", "ECO 4", "2026-10-07T11:31:14"),
        _item("lesechos", "ECO 3", "2026-10-07T11:31:13"),
        _item("lesechos", "ECO 2", "2026-10-07T11:31:12"),
        _item("lesechos", "ECO 1", "2026-10-07T11:31:11"),
        _item("figaro", "FIG 1", "2026-10-07T11:31:10"),
        _item("france", "LM 1", "2026-10-07T11:31:09"),
        _item("france24", "F24 1", "2026-10-07T11:31:08"),
        _item("spiegel", "SPG 1", "2026-10-07T11:31:07"),
    ]

    result = news.prepare_button_candidates(pool)

    assert [item["source"] for item in result] == [
        "lesechos",
        "figaro",
        "france",
        "france24",
        "spiegel",
    ]


def test_button_candidates_backfill_when_fewer_than_five_sources_exist():
    pool = [
        _item("lesechos", "ECO 3", "2026-10-07T11:31:15"),
        _item("lesechos", "ECO 2", "2026-10-07T11:31:14"),
        _item("france", "LM 2", "2026-10-07T11:31:13"),
        _item("lesechos", "ECO 1", "2026-10-07T11:31:12"),
        _item("france", "LM 1", "2026-10-07T11:31:11"),
    ]

    result = news.prepare_button_candidates(pool)

    assert len(result) == 5
    assert [item["source"] for item in result[:2]] == ["lesechos", "france"]


def test_local_ai_installer_uses_site_local_paths_and_loopback_only():
    script = (
        ROOT / "scripts/install-local-ai-sorter-service.sh"
    ).read_text(encoding="utf-8")

    assert "/home/gerd" not in script
    assert "--host 127.0.0.1 --port 8080" in script
    assert "VICKY_LLAMA_SERVER" in script
    assert "VICKY_AI_MODEL_PATH" in script
    assert "VICKY_AI_IMPORTANCE_SORT=1" in script


def test_release_version_is_9_1_2():
    assert (ROOT / "VERSION").read_text(encoding="utf-8").strip() == "9.1.2"
