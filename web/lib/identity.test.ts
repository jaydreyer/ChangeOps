// @vitest-environment node

import {
  SignJWT,
  exportJWK,
  exportSPKI,
  generateKeyPair,
} from "jose";
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  IdentityVerificationError,
  clearIdentityCachesForTests,
  verifiedIdentity,
} from "./identity";

const REGION = "us-east-1";
const USER_POOL = "us-east-1_fixture";
const ISSUER = `https://cognito-idp.${REGION}.amazonaws.com/${USER_POOL}`;
const CLIENT = "fixture-client";
const SIGNER = "arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/app/test/1";
const SUBJECT = "fixture-subject";

async function authenticationHeaders(options?: {
  groups?: string[];
  signer?: string;
  subjectHeader?: string;
}) {
  const albKeys = await generateKeyPair("ES256");
  const cognitoKeys = await generateKeyPair("RS256");
  const albKeyId = "alb-key";
  const cognitoKeyId = "cognito-key";
  const now = Math.floor(Date.now() / 1000);
  const claims = await new SignJWT({})
    .setProtectedHeader({
      alg: "ES256",
      kid: albKeyId,
      signer: options?.signer ?? SIGNER,
      client: CLIENT,
      iss: ISSUER,
      exp: now + 300,
    })
    .setSubject(SUBJECT)
    .setIssuedAt(now)
    .sign(albKeys.privateKey);
  const access = await new SignJWT({
    client_id: CLIENT,
    token_use: "access",
    "cognito:groups": options?.groups ?? ["admin"],
  })
    .setProtectedHeader({ alg: "RS256", kid: cognitoKeyId })
    .setIssuer(ISSUER)
    .setSubject(SUBJECT)
    .setIssuedAt(now)
    .setExpirationTime(now + 300)
    .sign(cognitoKeys.privateKey);
  const albPublicKey = await exportSPKI(albKeys.publicKey);
  const cognitoPublicKey = {
    ...(await exportJWK(cognitoKeys.publicKey)),
    kid: cognitoKeyId,
    alg: "RS256",
    use: "sig",
  };
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: string | URL | Request) => {
      const url = String(input);
      if (url.includes("public-keys.auth.elb")) return new Response(albPublicKey);
      if (url.endsWith("/.well-known/jwks.json")) {
        return Response.json({ keys: [cognitoPublicKey] });
      }
      throw new Error(`Unexpected fixture URL: ${url}`);
    }),
  );
  return new Headers({
    "x-amzn-oidc-data": claims,
    "x-amzn-oidc-identity": options?.subjectHeader ?? SUBJECT,
    "x-amzn-oidc-accesstoken": access,
    "x-changeops-actor": "browser-controlled",
    "x-changeops-role": "admin",
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
  clearIdentityCachesForTests();
});

function configureAlbMode() {
  vi.stubEnv("CHANGEOPS_IDENTITY_MODE", "alb");
  vi.stubEnv("AWS_REGION", REGION);
  vi.stubEnv("ALB_EXPECTED_SIGNER_ARN", SIGNER);
  vi.stubEnv("COGNITO_USER_POOL_ID", USER_POOL);
  vi.stubEnv("COGNITO_CLIENT_ID", CLIENT);
}

describe("verifiedIdentity", () => {
  it("maps signed ALB and Cognito claims to the immutable subject and one role", async () => {
    configureAlbMode();

    await expect(verifiedIdentity(await authenticationHeaders())).resolves.toEqual({
      actor: SUBJECT,
      role: "admin",
    });
  });

  it("fails closed when the ALB signer does not match the configured load balancer", async () => {
    configureAlbMode();

    await expect(
      verifiedIdentity(await authenticationHeaders({ signer: `${SIGNER}-forged` })),
    ).rejects.toBeInstanceOf(IdentityVerificationError);
  });

  it("fails closed for missing, multiple, or unknown privileged groups", async () => {
    configureAlbMode();

    for (const groups of [[], ["admin", "reviewer"], ["operator"]]) {
      clearIdentityCachesForTests();
      await expect(
        verifiedIdentity(await authenticationHeaders({ groups })),
      ).rejects.toBeInstanceOf(IdentityVerificationError);
    }
  });

  it("requires the signed subject to match the ALB subject header", async () => {
    configureAlbMode();

    await expect(
      verifiedIdentity(await authenticationHeaders({ subjectHeader: "different-subject" })),
    ).rejects.toBeInstanceOf(IdentityVerificationError);
  });

  it("retains explicit local demonstration headers outside deployed mode", async () => {
    vi.stubEnv("CHANGEOPS_IDENTITY_MODE", "demo");

    await expect(
      verifiedIdentity(
        new Headers({
          "x-changeops-actor": "local-reviewer",
          "x-changeops-role": "reviewer",
        }),
      ),
    ).resolves.toEqual({ actor: "local-reviewer", role: "reviewer" });
  });
});
