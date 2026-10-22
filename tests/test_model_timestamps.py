"""Timestamp defaults are evaluated for each instance, not at module import."""

import json
from datetime import datetime, timedelta, timezone

import pytest

from context_bridge import models


@pytest.fixture(
    params=[
        (
            models.Memory,
            {
                "content": "synthetic memory",
                "memory_type": "decision",
                "source_agent": "test",
                "session_id": "synthetic-session",
                "project_path": "fixture-project",
            },
            ("created_at", "updated_at"),
        ),
        (
            models.Session,
            {
                "session_id": "synthetic-session",
                "agent": "test",
                "project_path": "fixture-project",
                "file_path": "fixture.json",
                "content": "synthetic session",
            },
            ("created_at",),
        ),
    ],
    ids=["memory", "session"],
)
def model_case(request):
    return request.param


@pytest.mark.parametrize("from_json", [False, True], ids=["constructor", "json"])
def test_defaults_use_the_construction_time(monkeypatch, model_case, from_json):
    model, data, fields = model_case
    first_time = datetime(2020, 1, 2, 3, 4, 5, 123456, tzinfo=timezone.utc)
    second_time = first_time + timedelta(seconds=1)
    calls = []

    class Clock:
        current = first_time

        @classmethod
        def now(cls, *, tz):
            calls.append(tz)
            return cls.current

    monkeypatch.setattr(models, "datetime", Clock)

    def create():
        return (
            model.model_validate_json(json.dumps(data)) if from_json else model(**data)
        )

    first = create()
    Clock.current = second_time
    second = create()

    for field in fields:
        assert getattr(first, field) == first_time
        assert getattr(second, field) == second_time
        assert getattr(second, field).utcoffset() == timedelta(0)
    assert calls == [timezone.utc] * (2 * len(fields))


def test_explicit_timestamps_survive_json_round_trip(monkeypatch, model_case):
    model, data, fields = model_case

    class UnusedClock:
        @classmethod
        def now(cls, *, tz):
            pytest.fail("An explicit timestamp must not invoke the default clock")

    monkeypatch.setattr(models, "datetime", UnusedClock)
    timestamp = datetime(
        2020, 1, 2, 3, 4, 5, 678901, tzinfo=timezone(timedelta(hours=5, minutes=30))
    )
    explicit = {field: timestamp for field in fields}
    original = model(**data, **explicit)
    restored = model.model_validate_json(original.model_dump_json())

    for field in fields:
        assert getattr(original, field) == timestamp
        assert getattr(restored, field) == timestamp
        assert getattr(restored, field).microsecond == 678901
        assert getattr(restored, field).utcoffset() == timedelta(hours=5, minutes=30)
