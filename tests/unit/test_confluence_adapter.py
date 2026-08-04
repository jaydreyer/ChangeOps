import io
import json
from pathlib import Path
from urllib.error import HTTPError, URLError

import pytest

from changeops.adapters import confluence
from changeops.adapters.confluence import ConfluenceAdapterError, ConfluenceCloudAdapter

FIXTURE_DIR = Path(__file__).parents[1] / "fixtures" / "confluence"


def _fixture(name: str) -> bytes:
    return (FIXTURE_DIR / name).read_bytes()


class Response:
    status = 200

    def __init__(self, body: bytes) -> None:
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def read(self) -> bytes:
        return self.body


def _adapter() -> ConfluenceCloudAdapter:
    return ConfluenceCloudAdapter(
        base_url="https://acme.atlassian.net",
        email="reader@example.com",
        api_token="secret",
        timeout_seconds=4,
    )


def test_adapter_reads_bounded_page_and_space_metadata(monkeypatch) -> None:
    requests = []

    def fake_urlopen(request, timeout):
        requests.append((request, timeout))
        body = _fixture("space.json") if "/spaces/" in request.full_url else _fixture("page.json")
        return Response(body)

    monkeypatch.setattr(confluence, "urlopen", fake_urlopen)
    metadata = _adapter().get_page_metadata("123456789")

    assert [request.full_url for request, _ in requests] == [
        "https://acme.atlassian.net/wiki/api/v2/pages/123456789?include-version=true",
        "https://acme.atlassian.net/wiki/api/v2/spaces/987654321",
    ]
    assert all(timeout == 4 for _, timeout in requests)
    assert all(request.headers["Authorization"].startswith("Basic ") for request, _ in requests)
    assert metadata.page_id == "123456789"
    assert metadata.title == "Manager Travel Approval Guide"
    assert metadata.space_id == "987654321"
    assert metadata.space_key == "TRAVEL"
    assert metadata.version == 7
    assert metadata.status == "current"
    assert metadata.source_updated_at.isoformat() == "2026-08-01T16:30:00+00:00"
    assert metadata.canonical_url == (
        "https://acme.atlassian.net/wiki/spaces/TRAVEL/pages/123456789"
    )


@pytest.mark.parametrize(
    ("status", "result"),
    [
        (401, "authentication_failure"),
        (403, "permission_denied"),
        (404, "page_not_found"),
        (400, "validation_failure"),
        (429, "provider_unavailable"),
        (503, "provider_unavailable"),
    ],
)
def test_adapter_classifies_provider_failures(monkeypatch, status: int, result: str) -> None:
    monkeypatch.setattr(
        confluence,
        "urlopen",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            HTTPError("url", status, "error", {}, io.BytesIO(b"{}"))
        ),
    )

    with pytest.raises(ConfluenceAdapterError) as captured:
        _adapter().get_page_metadata("123456789")

    assert captured.value.result == result


def test_adapter_classifies_network_and_ambiguous_responses(monkeypatch) -> None:
    monkeypatch.setattr(
        confluence,
        "urlopen",
        lambda *args, **kwargs: (_ for _ in ()).throw(URLError("lost")),
    )
    with pytest.raises(ConfluenceAdapterError) as unavailable:
        _adapter().get_page_metadata("123456789")
    assert unavailable.value.result == "provider_unavailable"

    monkeypatch.setattr(confluence, "urlopen", lambda *args, **kwargs: Response(b"not-json"))
    with pytest.raises(ConfluenceAdapterError) as ambiguous:
        _adapter().get_page_metadata("123456789")
    assert ambiguous.value.result == "ambiguous_response"


def test_adapter_rejects_mismatched_identity_and_invalid_status(monkeypatch) -> None:
    page = json.loads(_fixture("page.json"))
    page["id"] = "222"
    monkeypatch.setattr(
        confluence,
        "urlopen",
        lambda *args, **kwargs: Response(json.dumps(page).encode()),
    )
    with pytest.raises(ConfluenceAdapterError) as mismatch:
        _adapter().get_page_metadata("123456789")
    assert mismatch.value.result == "validation_failure"

    with pytest.raises(ConfluenceAdapterError) as invalid_id:
        _adapter().get_page_metadata("placeholder")
    assert invalid_id.value.result == "validation_failure"


def test_adapter_rejects_non_https_site_origin() -> None:
    with pytest.raises(ValueError):
        ConfluenceCloudAdapter(
            base_url="http://acme.atlassian.net",
            email="reader@example.com",
            api_token="secret",
            timeout_seconds=4,
        )
