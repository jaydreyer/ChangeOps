import { apiBaseUrl } from "@/lib/api";
import { requestId } from "@/lib/request-id";

export const dynamic = "force-dynamic";

export async function GET(request: Request = new Request("http://localhost/readyz")) {
  const correlationId = requestId(request.headers);
  try {
    const response = await fetch(new URL("/healthz", apiBaseUrl()), {
      cache: "no-store",
      headers: { "x-request-id": correlationId },
      signal: AbortSignal.timeout(3_000),
    });
    const payload = await response.json();
    if (!response.ok || payload?.status !== "ok") throw new Error("api_not_ready");
    return Response.json(
      { status: "ok", api: "ok" },
      { headers: { "cache-control": "no-store", "x-request-id": correlationId } },
    );
  } catch {
    return Response.json(
      { status: "unavailable", api: "unavailable" },
      {
        status: 503,
        headers: { "cache-control": "no-store", "x-request-id": correlationId },
      },
    );
  }
}
