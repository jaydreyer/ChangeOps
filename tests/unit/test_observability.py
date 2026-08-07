import json
import logging

from changeops.observability import JsonLogFormatter, normalized_request_id


def test_request_id_accepts_safe_correlation_value_and_replaces_control_characters() -> None:
    assert normalized_request_id("request-123") == "request-123"
    generated = normalized_request_id("unsafe\nvalue")
    assert generated != "unsafe\nvalue"
    assert len(generated) == 36


def test_json_formatter_emits_only_whitelisted_structured_fields() -> None:
    record = logging.LogRecord(
        name="changeops.http",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="Request completed.",
        args=(),
        exc_info=None,
    )
    record.request_id = "request-123"
    record.event = "request_completed"
    record.path = "/healthz"
    record.authorization = "Bearer must-not-appear"

    payload = json.loads(JsonLogFormatter().format(record))

    assert payload == {
        "event": "request_completed",
        "level": "info",
        "logger": "changeops.http",
        "message": "Request completed.",
        "path": "/healthz",
        "request_id": "request-123",
    }
    assert "must-not-appear" not in json.dumps(payload)
