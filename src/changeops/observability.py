import json
import logging
import re
import sys
import uuid
from contextvars import ContextVar
from time import monotonic

from fastapi import FastAPI, Request

REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,100}$")
request_id_context: ContextVar[str | None] = ContextVar("request_id", default=None)
logger = logging.getLogger("changeops.http")


class JsonLogFormatter(logging.Formatter):
    _extra_fields = (
        "elapsed_ms",
        "event",
        "method",
        "path",
        "request_id",
        "status_code",
    )

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "level": record.levelname.lower(),
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", None) or request_id_context.get(),
        }
        for field in self._extra_fields:
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        return json.dumps(payload, separators=(",", ":"), sort_keys=True)


def configure_structured_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonLogFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)
    for logger_name in ("changeops", "uvicorn", "uvicorn.error", "uvicorn.access"):
        configured = logging.getLogger(logger_name)
        configured.handlers = []
        configured.propagate = True


def normalized_request_id(value: str | None) -> str:
    candidate = (value or "").strip()
    return candidate if REQUEST_ID_PATTERN.fullmatch(candidate) else str(uuid.uuid4())


def install_request_logging(app: FastAPI) -> None:
    @app.middleware("http")
    async def correlate_and_log(request: Request, call_next):
        request_id = normalized_request_id(request.headers.get("x-request-id"))
        token = request_id_context.set(request_id)
        request.state.request_id = request_id
        started_at = monotonic()
        try:
            response = await call_next(request)
        except Exception:
            logger.error(
                "Request failed.",
                extra={
                    "event": "request_failed",
                    "method": request.method,
                    "path": request.url.path,
                    "request_id": request_id,
                    "elapsed_ms": round((monotonic() - started_at) * 1000),
                },
            )
            raise
        else:
            response.headers["X-Request-ID"] = request_id
            logger.info(
                "Request completed.",
                extra={
                    "event": "request_completed",
                    "method": request.method,
                    "path": request.url.path,
                    "request_id": request_id,
                    "status_code": response.status_code,
                    "elapsed_ms": round((monotonic() - started_at) * 1000),
                },
            )
            return response
        finally:
            request_id_context.reset(token)
