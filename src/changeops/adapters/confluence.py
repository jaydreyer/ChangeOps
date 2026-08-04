import base64
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen


class ConfluenceAdapterError(Exception):
    def __init__(self, result: str, message: str) -> None:
        super().__init__(message)
        self.result = result
        self.message = message


@dataclass(frozen=True)
class ConfluencePageMetadata:
    page_id: str
    title: str
    canonical_url: str
    space_id: str
    space_key: str
    version: int
    status: str
    source_updated_at: datetime


class ConfluenceCloudAdapter:
    def __init__(
        self, *, base_url: str, email: str, api_token: str, timeout_seconds: float
    ) -> None:
        normalized_url = base_url.rstrip("/")
        parsed_url = urlparse(normalized_url)
        if (
            parsed_url.scheme != "https"
            or not parsed_url.netloc
            or parsed_url.username
            or parsed_url.password
            or parsed_url.query
            or parsed_url.fragment
        ):
            raise ValueError("Confluence base URL must be an HTTPS site origin.")
        self.base_url = normalized_url
        self.email = email
        self.api_token = api_token
        self.timeout_seconds = timeout_seconds

    def get_page_metadata(self, page_id: str) -> ConfluencePageMetadata:
        if not page_id.isdigit() or len(page_id) > 100:
            raise ConfluenceAdapterError(
                "validation_failure",
                "The configured Confluence page ID must be numeric.",
            )
        page = self._get_json(
            f"/wiki/api/v2/pages/{quote(page_id, safe='')}?include-version=true",
            resource="page",
        )
        returned_page_id = _required_string(page, "id")
        if returned_page_id != page_id:
            raise ConfluenceAdapterError(
                "validation_failure",
                "Confluence returned a different page identity than the configured page.",
            )
        space_id = _bounded_string(page, "spaceId", 100)
        space = self._get_json(
            f"/wiki/api/v2/spaces/{quote(space_id, safe='')}",
            resource="space",
        )
        if _required_string(space, "id") != space_id:
            raise ConfluenceAdapterError(
                "validation_failure",
                "Confluence returned a space that does not own the configured page.",
            )

        version = page.get("version")
        if not isinstance(version, dict):
            raise _ambiguous_response()
        version_number = version.get("number")
        if (
            not isinstance(version_number, int)
            or isinstance(version_number, bool)
            or version_number < 1
        ):
            raise _ambiguous_response()
        status = _required_string(page, "status")
        if status not in {"current", "draft", "archived"}:
            raise ConfluenceAdapterError(
                "validation_failure",
                "Confluence returned an unsupported page status.",
            )
        source_updated_at = _parse_timestamp(_required_string(version, "createdAt"))
        space_key = _bounded_string(space, "key", 100)
        canonical_url = (
            f"{self.base_url}/wiki/spaces/{quote(space_key, safe='')}/pages/"
            f"{quote(returned_page_id, safe='')}"
        )
        return ConfluencePageMetadata(
            page_id=returned_page_id,
            title=_bounded_string(page, "title", 300),
            canonical_url=canonical_url,
            space_id=space_id,
            space_key=space_key,
            version=version_number,
            status=status,
            source_updated_at=source_updated_at,
        )

    def _get_json(self, path: str, *, resource: str) -> dict[str, Any]:
        token = base64.b64encode(f"{self.email}:{self.api_token}".encode()).decode()
        request = Request(
            f"{self.base_url}{path}",
            headers={
                "Accept": "application/json",
                "Authorization": f"Basic {token}",
            },
            method="GET",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:  # noqa: S310
                status = response.status
                raw = response.read()
        except HTTPError as error:
            if error.code == 401:
                raise ConfluenceAdapterError(
                    "authentication_failure",
                    "Confluence rejected the configured credentials.",
                ) from error
            if error.code == 403:
                raise ConfluenceAdapterError(
                    "permission_denied",
                    "Confluence denied access to the configured page or space.",
                ) from error
            if error.code == 404:
                result = "page_not_found" if resource == "page" else "validation_failure"
                raise ConfluenceAdapterError(
                    result,
                    f"The configured Confluence {resource} was not found.",
                ) from error
            if 400 <= error.code < 500 and error.code != 429:
                raise ConfluenceAdapterError(
                    "validation_failure",
                    "Confluence rejected the bounded metadata request.",
                ) from error
            raise ConfluenceAdapterError(
                "provider_unavailable",
                "Confluence is temporarily unavailable.",
            ) from error
        except (TimeoutError, URLError, OSError) as error:
            raise ConfluenceAdapterError(
                "provider_unavailable",
                "Confluence is temporarily unavailable.",
            ) from error

        if status != 200:
            raise _ambiguous_response()
        try:
            payload = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise _ambiguous_response() from error
        if not isinstance(payload, dict):
            raise _ambiguous_response()
        return payload


def _required_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise _ambiguous_response()
    return value.strip()


def _bounded_string(payload: dict[str, Any], key: str, max_length: int) -> str:
    value = _required_string(payload, key)
    if len(value) > max_length:
        raise ConfluenceAdapterError(
            "validation_failure",
            "Confluence returned metadata that exceeds the supported field length.",
        )
    return value


def _parse_timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise _ambiguous_response() from error
    if parsed.tzinfo is None:
        raise _ambiguous_response()
    return parsed


def _ambiguous_response() -> ConfluenceAdapterError:
    return ConfluenceAdapterError(
        "ambiguous_response",
        "Confluence returned an incomplete or unreadable metadata response.",
    )
