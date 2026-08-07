import { NextRequest, NextResponse } from "next/server";
import { apiBaseUrl } from "@/lib/api";
import {
  IdentityVerificationError,
  identityMode,
  verifiedIdentity,
} from "@/lib/identity";
import { requestId } from "@/lib/request-id";

async function proxy(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const correlationId = requestId(request.headers);
  const { path } = await context.params;
  const upstream = new URL(`/api/${path.join("/")}`, apiBaseUrl());
  upstream.search = request.nextUrl.search;
  const headers = new Headers();
  const contentType = request.headers.get("content-type");
  if (contentType) headers.set("content-type", contentType);
  headers.set("x-request-id", correlationId);

  try {
    if (identityMode() === "alb") {
      const identity = await verifiedIdentity(request.headers);
      headers.set("x-changeops-actor", identity.actor);
      headers.set("x-changeops-role", identity.role);
    } else {
      for (const name of ["x-changeops-actor", "x-changeops-role"]) {
        const value = request.headers.get(name);
        if (value) headers.set(name, value);
      }
    }
  } catch (error) {
    if (error instanceof IdentityVerificationError) {
      console.warn(
        JSON.stringify({
          event: "proxy_identity_rejected",
          level: "warning",
          method: request.method,
          path: request.nextUrl.pathname,
          request_id: correlationId,
        }),
      );
      return NextResponse.json(
        {
          detail: {
            code: "identity_verification_failed",
            message: "A valid authenticated ChangeOps identity is required.",
          },
        },
        { status: 401, headers: { "x-request-id": correlationId } },
      );
    }
    throw error;
  }

  const startedAt = performance.now();
  try {
    const response = await fetch(upstream, {
      method: request.method,
      headers,
      body: request.method === "GET" || request.method === "HEAD" ? undefined : await request.text(),
      cache: "no-store",
    });
    console.info(
      JSON.stringify({
        event: "proxy_request_completed",
        level: "info",
        method: request.method,
        path: request.nextUrl.pathname,
        request_id: correlationId,
        status_code: response.status,
        elapsed_ms: Math.round(performance.now() - startedAt),
      }),
    );
    return new NextResponse(response.body, {
      status: response.status,
      headers: {
        "content-type": response.headers.get("content-type") ?? "application/json",
        "x-request-id": correlationId,
      },
    });
  } catch {
    console.error(
      JSON.stringify({
        event: "proxy_request_failed",
        level: "error",
        method: request.method,
        path: request.nextUrl.pathname,
        request_id: correlationId,
        elapsed_ms: Math.round(performance.now() - startedAt),
      }),
    );
    return NextResponse.json(
      {
        detail: {
          code: "api_unavailable",
          message: "The ChangeOps API is unavailable.",
        },
      },
      { status: 503, headers: { "x-request-id": correlationId } },
    );
  }
}

export const GET = proxy;
export const POST = proxy;
