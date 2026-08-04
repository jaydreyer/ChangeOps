from fastapi import APIRouter
from fastapi.exceptions import HTTPException

from changeops.api.dependencies import SessionDependency
from changeops.schemas.catalog import (
    CatalogBrowseResponse,
    CatalogObjectDetailResponse,
    PolicyRuleReferenceResponse,
)
from changeops.services.catalog_projection_service import (
    CatalogObjectNotFoundError,
    CatalogOrganizationNotFoundError,
    CatalogProjectionIntegrityError,
    PolicyChangeNotFoundError,
    PolicyRuleReferenceNotFoundError,
    UnsupportedCatalogObjectTypeError,
    get_catalog_browse,
    get_catalog_object_detail,
    get_policy_rule_reference,
)

router = APIRouter(prefix="/api/v1", tags=["enterprise-knowledge-catalog"])


@router.get("/catalog-objects", response_model=CatalogBrowseResponse)
def retrieve_catalog_objects(
    organization_id: str,
    session: SessionDependency,
    object_type: str | None = None,
) -> CatalogBrowseResponse:
    try:
        return get_catalog_browse(session, organization_id, object_type)
    except CatalogOrganizationNotFoundError as error:
        raise _http_error(404, "organization_not_found", "Organization was not found.") from error
    except UnsupportedCatalogObjectTypeError as error:
        raise _http_error(
            422,
            "unsupported_catalog_object_type",
            "Catalog object type is not supported by this explorer.",
        ) from error


@router.get(
    "/catalog-objects/{object_type}/{object_id}",
    response_model=CatalogObjectDetailResponse,
)
def retrieve_catalog_object(
    object_type: str,
    object_id: str,
    session: SessionDependency,
    organization_id: str | None = None,
) -> CatalogObjectDetailResponse:
    try:
        return get_catalog_object_detail(
            session,
            object_type,
            object_id,
            organization_id=organization_id,
        )
    except UnsupportedCatalogObjectTypeError as error:
        raise _http_error(
            422,
            "unsupported_catalog_object_type",
            "Catalog object type is not supported by this explorer.",
        ) from error
    except CatalogObjectNotFoundError as error:
        raise _http_error(
            404,
            "catalog_object_not_found",
            "Catalog object was not found.",
        ) from error
    except CatalogProjectionIntegrityError as error:
        raise _http_error(409, "catalog_projection_inconsistent", str(error)) from error


@router.get(
    "/policy-changes/{policy_change_id}/rule-references/{rule_code}",
    response_model=PolicyRuleReferenceResponse,
)
def retrieve_policy_rule_reference(
    policy_change_id: str,
    rule_code: str,
    session: SessionDependency,
) -> PolicyRuleReferenceResponse:
    try:
        return get_policy_rule_reference(session, policy_change_id, rule_code)
    except PolicyChangeNotFoundError as error:
        raise _http_error(
            404,
            "policy_change_not_found",
            "Policy change was not found.",
        ) from error
    except PolicyRuleReferenceNotFoundError as error:
        raise _http_error(
            404,
            "policy_rule_reference_not_found",
            "Policy-scoped rule reference was not found.",
        ) from error
    except CatalogProjectionIntegrityError as error:
        raise _http_error(409, "catalog_projection_inconsistent", str(error)) from error


def _http_error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"code": code, "message": message})
