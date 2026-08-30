import ai_importance_sorter as sorter


def test_ai_sort_reorders_only(monkeypatch):
    messages = [
        {"text": "First", "headlines": ["Original first"]},
        {"text": "Second", "headlines": ["Original second"]},
        {"text": "Third", "headlines": ["Original third"]},
    ]
    original_snapshots = [dict(message) for message in messages]

    monkeypatch.setattr(sorter, "_enabled", lambda: True)
    monkeypatch.setattr(sorter, "_request_order", lambda _messages: [3, 1, 2])

    result = sorter.sort_messages_by_ai_importance(messages)

    assert result == [messages[2], messages[0], messages[1]]
    assert result[0] is messages[2]
    assert result[1] is messages[0]
    assert result[2] is messages[1]
    assert messages == original_snapshots


def test_ai_can_confirm_existing_order(monkeypatch):
    messages = [{"text": "First"}, {"text": "Second"}, {"text": "Third"}]
    logged = []

    monkeypatch.setattr(sorter, "_enabled", lambda: True)
    monkeypatch.setattr(sorter, "_request_order", lambda _messages: [1, 2, 3])

    result = sorter.sort_messages_by_ai_importance(messages, log=logged.append)

    assert result == messages
    assert all(result[index] is messages[index] for index in range(len(messages)))
    assert logged == ["AI importance sort completed: priority/order unchanged"]


def test_invalid_ai_order_keeps_existing_order(monkeypatch):
    messages = [
        {"text": "First"},
        {"text": "Second"},
        {"text": "Third"},
    ]

    monkeypatch.setattr(sorter, "_enabled", lambda: True)
    monkeypatch.setattr(sorter, "_request_order", lambda _messages: [1, 1, 3])

    result = sorter.sort_messages_by_ai_importance(messages)

    assert result == messages
    assert all(result[index] is messages[index] for index in range(len(messages)))


def test_disabled_ai_keeps_existing_order(monkeypatch):
    messages = [{"text": "First"}, {"text": "Second"}]
    monkeypatch.setattr(sorter, "_enabled", lambda: False)

    result = sorter.sort_messages_by_ai_importance(messages)

    assert result == messages
    assert result[0] is messages[0]
    assert result[1] is messages[1]
