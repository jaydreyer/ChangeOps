import { describe, expect, it } from "vitest";
import nextConfig from "./next.config";

describe("production security headers", () => {
  it("applies the reviewed browser controls to every route", async () => {
    const configuredHeaders = await nextConfig.headers?.();

    expect(configuredHeaders).toEqual([
      {
        source: "/:path*",
        headers: expect.arrayContaining([
          {
            key: "Strict-Transport-Security",
            value: "max-age=31536000; includeSubDomains",
          },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          {
            key: "Permissions-Policy",
            value: "camera=(), geolocation=(), microphone=()",
          },
        ]),
      },
    ]);
  });
});
