import base64
import json
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from changeops.domain.jira_execution import CreateJiraIssueParameters


class JiraAdapterError(Exception):
    def __init__(self, code: str, message: str, *, definitive_no_side_effect: bool) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.definitive_no_side_effect = definitive_no_side_effect


@dataclass(frozen=True)
class JiraIssueReceipt:
    issue_id: str
    issue_key: str
    api_url: str
    browse_url: str


class JiraCloudAdapter:
    def __init__(
        self, *, base_url: str, email: str, api_token: str, timeout_seconds: float
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.email = email
        self.api_token = api_token
        self.timeout_seconds = timeout_seconds

    def create_issue(self, parameters: CreateJiraIssueParameters) -> JiraIssueReceipt:
        project_reference = (
            {"id": parameters.project_id_or_key}
            if parameters.project_id_or_key.isdigit()
            else {"key": parameters.project_id_or_key}
        )
        payload = {
            "fields": {
                "project": project_reference,
                "issuetype": {"id": parameters.issue_type_id},
                "summary": parameters.summary,
                "description": parameters.description,
            },
            "properties": [
                {
                    "key": "changeops.execution-command",
                    "value": {"execution_command_id": parameters.execution_command_id},
                }
            ],
        }
        token = base64.b64encode(f"{self.email}:{self.api_token}".encode()).decode()
        request = Request(
            f"{self.base_url}/rest/api/3/issue",
            data=json.dumps(payload, separators=(",", ":")).encode(),
            headers={
                "Accept": "application/json",
                "Authorization": f"Basic {token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:  # noqa: S310
                status = response.status
                raw = response.read()
        except HTTPError as error:
            if error.code in {401, 403}:
                raise JiraAdapterError(
                    "jira_authentication_failed",
                    "Jira rejected the configured credentials or project permission.",
                    definitive_no_side_effect=True,
                ) from error
            if 400 <= error.code < 500 and error.code != 429:
                raise JiraAdapterError(
                    "jira_validation_failed",
                    "Jira rejected the configured project, Task type, or issue fields.",
                    definitive_no_side_effect=True,
                ) from error
            raise JiraAdapterError(
                "jira_unavailable",
                "Jira did not provide a confirmed create-issue result.",
                definitive_no_side_effect=error.code == 429,
            ) from error
        except (TimeoutError, URLError, OSError) as error:
            raise JiraAdapterError(
                "jira_unavailable",
                "Jira did not provide a confirmed create-issue result.",
                definitive_no_side_effect=False,
            ) from error

        if status != 201:
            raise JiraAdapterError(
                "jira_unavailable",
                "Jira returned an unexpected create-issue response.",
                definitive_no_side_effect=False,
            )
        try:
            body = json.loads(raw)
            issue_id = str(body["id"]).strip()
            issue_key = str(body["key"]).strip()
            api_url = str(body["self"]).strip()
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            raise JiraAdapterError(
                "jira_unavailable",
                "Jira created an issue but returned an unreadable receipt.",
                definitive_no_side_effect=False,
            ) from error
        if not issue_id or not issue_key or not api_url:
            raise JiraAdapterError(
                "jira_unavailable",
                "Jira created an issue but returned an incomplete receipt.",
                definitive_no_side_effect=False,
            )
        return JiraIssueReceipt(
            issue_id=issue_id,
            issue_key=issue_key,
            api_url=api_url,
            browse_url=f"{self.base_url}/browse/{issue_key}",
        )
