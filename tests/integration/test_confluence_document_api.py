from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from changeops.adapters.confluence import ConfluenceAdapterError, ConfluencePageMetadata
from changeops.db.models import (
    ConfluenceDocumentSource,
    EnterpriseDocument,
    PolicyDocumentDependency,
)
from changeops.db.session import SessionLocal
from changeops.services import confluence_document_service
from changeops.services.demo_reset_service import reset_demo_workflows
from changeops.services.seed_service import POLICY_CHANGE_ID

DOCUMENT_ID = "document-manager-travel-approval-guide"
PAGE_ID = "123456789"
REFRESH_URL = f"/api/v1/catalog-objects/enterprise_document/{DOCUMENT_ID}/confluence-refresh"
DETAIL_URL = f"/api/v1/catalog-objects/enterprise_document/{DOCUMENT_ID}"


@pytest.fixture(autouse=True)
def clean_confluence_source():
    with SessionLocal.begin() as session:
        source = session.get(ConfluenceDocumentSource, DOCUMENT_ID)
        if source is not None:
            session.delete(source)
    yield
    with SessionLocal.begin() as session:
        source = session.get(ConfluenceDocumentSource, DOCUMENT_ID)
        if source is not None:
            session.delete(source)


class FakeAdapter:
    def __init__(
        self,
        metadata: ConfluencePageMetadata | None = None,
        error: ConfluenceAdapterError | None = None,
    ) -> None:
        self.metadata = metadata or _metadata()
        self.error = error
        self.calls: list[str] = []

    def get_page_metadata(self, page_id: str) -> ConfluencePageMetadata:
        self.calls.append(page_id)
        if self.error is not None:
            raise self.error
        return self.metadata


def _metadata(
    *,
    title: str = "Manager Travel Approval Guide",
    version: int = 7,
) -> ConfluencePageMetadata:
    return ConfluencePageMetadata(
        page_id=PAGE_ID,
        title=title,
        canonical_url=f"https://acme.atlassian.net/wiki/spaces/TRAVEL/pages/{PAGE_ID}",
        space_id="987654321",
        space_key="TRAVEL",
        version=version,
        status="current",
        source_updated_at=datetime(2026, 8, 1, 16, 30, tzinfo=UTC),
    )


def _configure(monkeypatch, adapter: FakeAdapter) -> None:
    monkeypatch.setattr(
        confluence_document_service,
        "_configured_page_id",
        lambda document_id: PAGE_ID if document_id == DOCUMENT_ID else None,
    )
    monkeypatch.setattr(
        confluence_document_service,
        "_configured_adapter",
        lambda: adapter,
    )


def test_refresh_requires_explicit_selected_document_configuration(client) -> None:
    response = client.post(REFRESH_URL)

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "confluence_not_configured"
    with SessionLocal() as session:
        assert session.get(ConfluenceDocumentSource, DOCUMENT_ID) is None


def test_refresh_imports_metadata_and_repeats_idempotently(client, monkeypatch) -> None:
    adapter = FakeAdapter()
    _configure(monkeypatch, adapter)

    first = client.post(REFRESH_URL)
    second = client.post(REFRESH_URL)

    assert first.status_code == second.status_code == 200
    assert first.json()["result"] == "success"
    assert second.json()["result"] == "already_current"
    assert adapter.calls == [PAGE_ID, PAGE_ID]
    source = second.json()["external_source"]
    assert source["provider_label"] == "Confluence Cloud"
    assert source["external_page_id"] == PAGE_ID
    assert source["external_title"] == "Manager Travel Approval Guide"
    assert source["space_key"] == "TRAVEL"
    assert source["external_version"] == 7
    assert source["external_status"] == "current"
    assert len(source["source_fingerprint"]) == 64

    detail = client.get(DETAIL_URL).json()
    assert detail["external_source_state"] == "imported"
    assert detail["external_source"]["canonical_url"].endswith(f"/pages/{PAGE_ID}")
    with SessionLocal() as session:
        assert len(list(session.scalars(select(ConfluenceDocumentSource)))) == 1


def test_refresh_updates_only_imported_metadata_fields(client, monkeypatch) -> None:
    adapter = FakeAdapter()
    _configure(monkeypatch, adapter)
    assert client.post(REFRESH_URL).status_code == 200

    adapter.metadata = _metadata(title="Manager Travel Approval Guide — Revised", version=8)
    refreshed = client.post(REFRESH_URL)

    assert refreshed.status_code == 200
    assert refreshed.json()["result"] == "success"
    assert refreshed.json()["external_source"]["external_title"].endswith("Revised")
    assert refreshed.json()["external_source"]["external_version"] == 8
    with SessionLocal() as session:
        document = session.get(EnterpriseDocument, DOCUMENT_ID)
        assert document is not None
        assert document.title == "Manager Travel Approval Guide"
        assert document.version == "2"
        assert document.status == "published"
        relationships = list(
            session.scalars(
                select(PolicyDocumentDependency)
                .where(PolicyDocumentDependency.document_id == DOCUMENT_ID)
                .order_by(PolicyDocumentDependency.id)
            )
        )
        assert [item.id for item in relationships] == [
            "dependency-policy-manager-guide",
            "dependency-policy-manager-guide-proposed",
        ]


@pytest.mark.parametrize(
    ("result", "status_code"),
    [
        ("authentication_failure", 502),
        ("permission_denied", 502),
        ("page_not_found", 404),
        ("provider_unavailable", 502),
        ("validation_failure", 409),
        ("ambiguous_response", 502),
    ],
)
def test_first_failed_refresh_is_visible_without_persisting_unvalidated_identity(
    client,
    monkeypatch,
    result: str,
    status_code: int,
) -> None:
    adapter = FakeAdapter(error=ConfluenceAdapterError(result, f"Controlled {result}."))
    _configure(monkeypatch, adapter)

    response = client.post(REFRESH_URL)

    assert response.status_code == status_code
    assert response.json()["detail"]["code"] == f"confluence_{result}"
    with SessionLocal() as session:
        assert session.get(ConfluenceDocumentSource, DOCUMENT_ID) is None


def test_failed_refresh_preserves_last_known_good_metadata(client, monkeypatch) -> None:
    adapter = FakeAdapter()
    _configure(monkeypatch, adapter)
    assert client.post(REFRESH_URL).status_code == 200
    with SessionLocal() as session:
        source = session.get(ConfluenceDocumentSource, DOCUMENT_ID)
        known_good = (
            source.external_title,
            source.external_version,
            source.source_updated_at,
            source.source_fingerprint,
            source.refreshed_at,
        )

    adapter.error = ConfluenceAdapterError(
        "permission_denied",
        "Confluence denied access to the configured page or space.",
    )
    failed = client.post(REFRESH_URL)

    assert failed.status_code == 502
    detail = client.get(DETAIL_URL).json()
    assert detail["external_source"]["last_refresh_result"] == "permission_denied"
    assert "denied access" in detail["external_source"]["last_refresh_message"]
    with SessionLocal() as session:
        source = session.get(ConfluenceDocumentSource, DOCUMENT_ID)
        assert (
            source.external_title,
            source.external_version,
            source.source_updated_at,
            source.source_fingerprint,
            source.refreshed_at,
        ) == known_good


def test_refresh_rejects_silent_retargeting_of_imported_identity(client, monkeypatch) -> None:
    adapter = FakeAdapter()
    _configure(monkeypatch, adapter)
    assert client.post(REFRESH_URL).status_code == 200
    monkeypatch.setattr(
        confluence_document_service,
        "_configured_page_id",
        lambda document_id: "222222222" if document_id == DOCUMENT_ID else None,
    )

    response = client.post(REFRESH_URL)

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "confluence_validation_failure"
    assert adapter.calls == [PAGE_ID]
    with SessionLocal() as session:
        source = session.get(ConfluenceDocumentSource, DOCUMENT_ID)
        assert source.external_page_id == PAGE_ID
        assert source.last_refresh_result == "validation_failure"


def test_refresh_does_not_change_assessment_behavior(client, monkeypatch) -> None:
    before = client.post(f"/api/v1/policy-changes/{POLICY_CHANGE_ID}/impact-assessments")
    assert before.status_code == 201
    adapter = FakeAdapter()
    _configure(monkeypatch, adapter)

    assert client.post(REFRESH_URL).status_code == 200
    after = client.post(f"/api/v1/policy-changes/{POLICY_CHANGE_ID}/impact-assessments")

    assert after.status_code == 201
    before_body = before.json()
    after_body = after.json()
    assert after_body["input_fingerprint"] == before_body["input_fingerprint"]
    assert after_body["summary"] == before_body["summary"]
    assert [
        (item["worker"]["id"], item["classification"], item["reason_codes"])
        for item in after_body["worker_results"]
    ] == [
        (item["worker"]["id"], item["classification"], item["reason_codes"])
        for item in before_body["worker_results"]
    ]
    assert [
        (
            impact["domain"],
            impact["object_type"],
            impact["source_key"],
            impact["classification"],
            impact["reason_code"],
        )
        for impacts in after_body["enterprise_impacts"].values()
        for impact in impacts
    ] == [
        (
            impact["domain"],
            impact["object_type"],
            impact["source_key"],
            impact["classification"],
            impact["reason_code"],
        )
        for impacts in before_body["enterprise_impacts"].values()
        for impact in impacts
    ]
    assert after_body["summary"]["enterprise_impacts"] == 18
    assert len(after_body["proposed_actions"]) == 13


def test_demo_reset_preserves_imported_confluence_identity(client, monkeypatch) -> None:
    adapter = FakeAdapter()
    _configure(monkeypatch, adapter)
    assert client.post(REFRESH_URL).status_code == 200
    before = client.get(DETAIL_URL).json()["external_source"]

    with SessionLocal.begin() as session:
        reset_demo_workflows(session)

    assert client.get(DETAIL_URL).json()["external_source"] == before
