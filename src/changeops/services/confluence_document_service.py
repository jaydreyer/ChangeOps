import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from changeops.adapters.confluence import (
    ConfluenceAdapterError,
    ConfluenceCloudAdapter,
    ConfluencePageMetadata,
)
from changeops.config import get_settings
from changeops.db.models import ConfluenceDocumentSource, EnterpriseDocument

MANAGER_GUIDE_DOCUMENT_ID = "document-manager-travel-approval-guide"


class ConfluenceDocumentNotFoundError(Exception):
    pass


class ConfluenceNotConfiguredError(Exception):
    pass


class ConfluenceRefreshError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class ConfluenceRefreshOutcome:
    result: str
    source: ConfluenceDocumentSource


def refresh_confluence_document(
    session: Session,
    document_id: str,
    *,
    adapter: ConfluenceCloudAdapter | None = None,
    configured_page_id: str | None = None,
    attempted_at: datetime | None = None,
) -> ConfluenceRefreshOutcome:
    document = session.get(EnterpriseDocument, document_id)
    if document is None:
        raise ConfluenceDocumentNotFoundError(document_id)

    existing = session.get(ConfluenceDocumentSource, document_id)
    if configured_page_id is None:
        configured_page_id = _configured_page_id(document_id)
    if not configured_page_id:
        raise ConfluenceNotConfiguredError(document_id)
    attempted_at = attempted_at or datetime.now(UTC)
    if existing is not None and existing.external_page_id != configured_page_id:
        error = ConfluenceAdapterError(
            "validation_failure",
            "The configured page ID does not match the document's imported external identity.",
        )
        _record_failed_refresh(session, document_id, error, attempted_at)
        raise ConfluenceRefreshError(
            "confluence_validation_failure",
            error.message,
        )

    if adapter is None:
        adapter = _configured_adapter()
    session.rollback()
    try:
        metadata = adapter.get_page_metadata(configured_page_id)
    except ConfluenceAdapterError as error:
        _record_failed_refresh(session, document_id, error, attempted_at)
        raise ConfluenceRefreshError(f"confluence_{error.result}", error.message) from error

    if metadata.page_id != configured_page_id:
        error = ConfluenceAdapterError(
            "validation_failure",
            "Confluence returned a different page identity than the configured page.",
        )
        _record_failed_refresh(session, document_id, error, attempted_at)
        raise ConfluenceRefreshError(f"confluence_{error.result}", error.message)

    fingerprint = _source_fingerprint(metadata)
    with session.begin():
        locked_document = session.scalar(
            select(EnterpriseDocument).where(EnterpriseDocument.id == document_id).with_for_update()
        )
        if locked_document is None:
            raise ConfluenceDocumentNotFoundError(document_id)
        source = session.get(ConfluenceDocumentSource, document_id)
        if source is not None and source.external_page_id != configured_page_id:
            raise ConfluenceRefreshError(
                "confluence_validation_failure",
                "The configured page ID does not match the document's imported external identity.",
            )
        result = (
            "already_current"
            if source is not None and source.source_fingerprint == fingerprint
            else "success"
        )
        message = (
            "Confluence metadata is already current."
            if result == "already_current"
            else "Confluence metadata was imported."
        )
        if source is None:
            source = ConfluenceDocumentSource(
                document_id=document_id,
                provider="confluence_cloud",
                external_page_id=metadata.page_id,
                external_title=metadata.title,
                canonical_url=metadata.canonical_url,
                space_id=metadata.space_id,
                space_key=metadata.space_key,
                external_version=metadata.version,
                external_status=metadata.status,
                source_updated_at=metadata.source_updated_at,
                imported_at=attempted_at,
                refreshed_at=attempted_at,
                source_fingerprint=fingerprint,
                last_refresh_result=result,
                last_refresh_message=message,
                last_refresh_attempted_at=attempted_at,
            )
            session.add(source)
        else:
            if result == "success":
                source.external_title = metadata.title
                source.canonical_url = metadata.canonical_url
                source.space_id = metadata.space_id
                source.space_key = metadata.space_key
                source.external_version = metadata.version
                source.external_status = metadata.status
                source.source_updated_at = metadata.source_updated_at
                source.source_fingerprint = fingerprint
            source.refreshed_at = attempted_at
            source.last_refresh_result = result
            source.last_refresh_message = message
            source.last_refresh_attempted_at = attempted_at
        session.flush()
        return ConfluenceRefreshOutcome(result=result, source=source)


def _configured_page_id(document_id: str) -> str | None:
    settings = get_settings()
    if document_id == MANAGER_GUIDE_DOCUMENT_ID:
        return settings.confluence_manager_travel_approval_guide_page_id
    return None


def _configured_adapter() -> ConfluenceCloudAdapter:
    settings = get_settings()
    if (
        not settings.confluence_base_url
        or not settings.confluence_email
        or settings.confluence_api_token is None
        or not settings.confluence_api_token.get_secret_value()
    ):
        raise ConfluenceNotConfiguredError("confluence_credentials")
    try:
        return ConfluenceCloudAdapter(
            base_url=settings.confluence_base_url,
            email=settings.confluence_email,
            api_token=settings.confluence_api_token.get_secret_value(),
            timeout_seconds=settings.confluence_timeout_seconds,
        )
    except ValueError as error:
        raise ConfluenceNotConfiguredError("confluence_base_url") from error


def _record_failed_refresh(
    session: Session,
    document_id: str,
    error: ConfluenceAdapterError,
    attempted_at: datetime,
) -> None:
    session.rollback()
    with session.begin():
        source = session.scalar(
            select(ConfluenceDocumentSource)
            .where(ConfluenceDocumentSource.document_id == document_id)
            .with_for_update()
        )
        if source is None:
            return
        source.last_refresh_result = error.result
        source.last_refresh_message = error.message
        source.last_refresh_attempted_at = attempted_at


def _source_fingerprint(metadata: ConfluencePageMetadata) -> str:
    payload = {
        "provider": "confluence_cloud",
        "external_page_id": metadata.page_id,
        "external_title": metadata.title,
        "canonical_url": metadata.canonical_url,
        "space_id": metadata.space_id,
        "space_key": metadata.space_key,
        "external_version": metadata.version,
        "external_status": metadata.status,
        "source_updated_at": metadata.source_updated_at.isoformat(),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()
