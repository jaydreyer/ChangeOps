import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";
import { IdentityVerificationError, verifiedIdentity } from "@/lib/identity";
import { GET } from "./route";

vi.mock("@/lib/identity", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/identity")>();
  return {
    ...actual,
    identityMode: vi.fn(() => "alb"),
    verifiedIdentity: vi.fn(),
  };
});

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("deployed API proxy identity boundary", () => {
  it("replaces browser-controlled actor headers with verified claim values", async () => {
    vi.mocked(verifiedIdentity).mockResolvedValue({
      actor: "cognito-subject",
      role: "reviewer",
    });
    const upstream = vi.fn().mockResolvedValue(Response.json({ status: "ok" }));
    vi.stubGlobal("fetch", upstream);
    const request = new NextRequest("https://changeops.example/api/v1/example", {
      headers: {
        "x-changeops-actor": "browser-attacker",
        "x-changeops-role": "admin",
        "x-request-id": "request-123",
      },
    });

    const response = await GET(request, { params: Promise.resolve({ path: ["v1", "example"] }) });

    expect(response.status).toBe(200);
    const forwarded = new Headers(upstream.mock.calls[0][1].headers);
    expect(forwarded.get("x-changeops-actor")).toBe("cognito-subject");
    expect(forwarded.get("x-changeops-role")).toBe("reviewer");
    expect(forwarded.get("x-request-id")).toBe("request-123");
    expect(response.headers.get("x-request-id")).toBe("request-123");
  });

  it("does not call FastAPI when claim verification fails", async () => {
    vi.mocked(verifiedIdentity).mockRejectedValue(new IdentityVerificationError());
    const upstream = vi.fn();
    vi.stubGlobal("fetch", upstream);
    const request = new NextRequest("https://changeops.example/api/v1/example", {
      headers: {
        "x-changeops-actor": "browser-attacker",
        "x-changeops-role": "admin",
      },
    });

    const response = await GET(request, { params: Promise.resolve({ path: ["v1", "example"] }) });

    expect(response.status).toBe(401);
    expect(upstream).not.toHaveBeenCalled();
    await expect(response.json()).resolves.toMatchObject({
      detail: { code: "identity_verification_failed" },
    });
  });
});
