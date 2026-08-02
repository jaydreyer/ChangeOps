import type { ApiError, ExecutionPreparation, Workbench } from "./types";

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
