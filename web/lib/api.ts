import type {
  ApiError,
  CatalogBrowse,
  CatalogObjectDetail,
  CatalogObjectType,
  ExecutionPreparation,
  PolicyComparison,
  PolicyAnalysisEntry,
  PolicyAnalysisJourney,
  PolicyRuleReference,
  Workbench,
} from "./types";

export function apiBaseUrl(): string {
  return (process.env.CHANGEOPS_API_BASE_URL ?? "http://localhost:8000").replace(/\/$/, "");
}

export async function parseApiError(response: Response): Promise<ApiError> {
  try {
    const body = (await response.json()) as {
      detail?: { code?: string; message?: string };
    };
    return {
      code: body.detail?.code ?? `http_${response.status}`,
      message: body.detail?.message ?? "The ChangeOps API could not complete the request.",
    };
  } catch {
    return {
      code: `http_${response.status}`,
      message: "The ChangeOps API returned an unreadable error.",
    };
  }
}

export async function getWorkbench(runId: string): Promise<Workbench> {
  const response = await fetch(`${apiBaseUrl()}/api/v1/action-approval-runs/${runId}/workbench`, {
    cache: "no-store",
  });
  if (!response.ok) {
    const error = await parseApiError(response);
    throw new Error(`${error.code}|${error.message}`);
  }
  return response.json() as Promise<Workbench>;
}

export async function getExecutionPreparation(runId: string): Promise<ExecutionPreparation> {
  const response = await fetch(
    `${apiBaseUrl()}/api/v1/action-approval-runs/${runId}/execution-commands`,
    { cache: "no-store" },
  );
  if (!response.ok) {
    const error = await parseApiError(response);
    throw new Error(`${error.code}|${error.message}`);
  }
  return response.json() as Promise<ExecutionPreparation>;
}

export async function getPolicyAnalysisEntry(): Promise<PolicyAnalysisEntry> {
  const response = await fetch(`${apiBaseUrl()}/api/v1/policy-analysis-entry`, {
    cache: "no-store",
  });
  if (!response.ok) {
    const error = await parseApiError(response);
    throw new Error(`${error.code}|${error.message}`);
  }
  return response.json() as Promise<PolicyAnalysisEntry>;
}

export async function getPolicyAnalysisJourney(runId: string): Promise<PolicyAnalysisJourney> {
  const response = await fetch(
    `${apiBaseUrl()}/api/v1/policy-analysis-runs/${encodeURIComponent(runId)}/journey`,
    { cache: "no-store" },
  );
  if (!response.ok) {
    const error = await parseApiError(response);
    throw new Error(`${error.code}|${error.message}`);
  }
  return response.json() as Promise<PolicyAnalysisJourney>;
}

export async function getPolicyComparison(comparisonId: string): Promise<PolicyComparison> {
  const response = await fetch(
    `${apiBaseUrl()}/api/v1/policy-comparisons/${encodeURIComponent(comparisonId)}`,
    { cache: "no-store" },
  );
  if (!response.ok) {
    const error = await parseApiError(response);
    throw new Error(`${error.code}|${error.message}`);
  }
  return response.json() as Promise<PolicyComparison>;
}

export async function getCatalogBrowse(
  organizationId: string,
  objectType?: CatalogObjectType,
): Promise<CatalogBrowse> {
  const query = new URLSearchParams({ organization_id: organizationId });
  if (objectType) query.set("object_type", objectType);
  const response = await fetch(`${apiBaseUrl()}/api/v1/catalog-objects?${query}`, {
    cache: "no-store",
  });
  if (!response.ok) {
    const error = await parseApiError(response);
    throw new Error(`${error.code}|${error.message}`);
  }
  return response.json() as Promise<CatalogBrowse>;
}

export async function getCatalogObject(
  objectType: string,
  objectId: string,
): Promise<CatalogObjectDetail> {
  const response = await fetch(
    `${apiBaseUrl()}/api/v1/catalog-objects/${encodeURIComponent(objectType)}/${encodeURIComponent(objectId)}`,
    { cache: "no-store" },
  );
  if (!response.ok) {
    const error = await parseApiError(response);
    throw new Error(`${error.code}|${error.message}`);
  }
  return response.json() as Promise<CatalogObjectDetail>;
}

export async function getPolicyRuleReference(
  policyChangeId: string,
  ruleCode: string,
): Promise<PolicyRuleReference> {
  const response = await fetch(
    `${apiBaseUrl()}/api/v1/policy-changes/${encodeURIComponent(policyChangeId)}/rule-references/${encodeURIComponent(ruleCode)}`,
    { cache: "no-store" },
  );
  if (!response.ok) {
    const error = await parseApiError(response);
    throw new Error(`${error.code}|${error.message}`);
  }
  return response.json() as Promise<PolicyRuleReference>;
}
