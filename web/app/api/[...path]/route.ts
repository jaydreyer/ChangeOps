import { NextRequest, NextResponse } from "next/server";
import { apiBaseUrl } from "@/lib/api";

async function proxy(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params;
  const upstream = new URL(`/api/${path.join("/")}`, apiBaseUrl());
  upstream.search = request.nextUrl.search;
  const headers = new Headers();
  for (const name of ["content-type", "x-changeops-actor", "x-changeops-role"]) {
    const value = request.headers.get(name);
    if (value) headers.set(name, value);
  }
  try {
    const response = await fetch(upstream, {
      method: request.method,
      headers,
      body: request.method === "GET" || request.method === "HEAD" ? undefined : await request.text(),
      cache: "no-store",
    });
    return new NextResponse(response.body, {
      status: response.status,
      headers: { "content-type": response.headers.get("content-type") ?? "application/json" },
    });
  } catch {
    return NextResponse.json(
      {
        detail: {
          code: "api_unavailable",
          message: "The ChangeOps API is unavailable. Check that the local stack is running.",
        },
      },
      { status: 503 },
    );
  }
}

export const GET = proxy;
export const POST = proxy;
