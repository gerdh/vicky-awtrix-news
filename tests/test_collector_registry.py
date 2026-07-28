from collectors.registry import CollectorRegistry


class GoodCollector:
    name = "good"

    def collect(self):
        return [
            {
                "id": "1",
                "source": "good",
                "title": "Valid headline",
                "published": False,
            }
        ]


class BrokenCollector:
    name = "broken"

    def collect(self):
        raise RuntimeError("offline")


class InvalidCollector:
    name = "invalid"

    def collect(self):
        return [{"source": "invalid", "title": ""}]


def test_registry_keeps_running_after_collector_failure():
    registry = CollectorRegistry()
    registry.register(BrokenCollector())
    registry.register(GoodCollector())

    items, results = registry.run_all()

    assert [item["title"] for item in items] == ["Valid headline"]
    assert len(results) == 2
    assert results[0].ok is False
    assert "RuntimeError: offline" in results[0].error
    assert results[1].ok is True


def test_registry_rejects_duplicate_names():
    registry = CollectorRegistry()
    registry.register(GoodCollector())

    try:
        registry.register(GoodCollector())
    except ValueError as error:
        assert "already registered" in str(error)
    else:
        raise AssertionError("duplicate collector was accepted")


def test_registry_isolates_invalid_collector_output():
    registry = CollectorRegistry()
    registry.register(InvalidCollector())
    registry.register(GoodCollector())

    items, results = registry.run_all()

    assert len(items) == 1
    assert results[0].ok is False
    assert "invalid item" in results[0].error
    assert results[1].ok is True
