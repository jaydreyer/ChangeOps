import {
  createRemoteJWKSet,
  decodeProtectedHeader,
  importSPKI,
  jwtVerify,
  type JWTPayload,
} from "jose";

const ALLOWED_ROLES = new Set(["reviewer", "admin"]);
const SAFE_KEY_ID = /^[A-Za-z0-9_-]{1,200}$/;
const SAFE_REGION = /^[a-z]{2}(?:-gov)?-[a-z]+-\d$/;
const CERTIFICATE_LIMIT_BYTES = 16_384;

export type ChangeOpsRole = "reviewer" | "admin";

export type VerifiedIdentity = {
  actor: string;
  role: ChangeOpsRole;
};

type IdentityMode = "demo" | "alb";

type IdentityConfiguration = {
  mode: IdentityMode;
  awsRegion?: string;
  expectedSignerArn?: string;
  cognitoClientId?: string;
  cognitoIssuer?: string;
};

export class IdentityVerificationError extends Error {
  constructor() {
    super("identity_verification_failed");
    this.name = "IdentityVerificationError";
  }
}

const albCertificateCache = new Map<string, CryptoKey>();
const cognitoJwksCache = new Map<string, ReturnType<typeof createRemoteJWKSet>>();

function configuration(environment: NodeJS.ProcessEnv = process.env): IdentityConfiguration {
  const mode = environment.CHANGEOPS_IDENTITY_MODE ?? "demo";
  if (mode === "demo") return { mode };
  if (mode !== "alb") throw new IdentityVerificationError();

  const awsRegion = environment.AWS_REGION;
  const expectedSignerArn = environment.ALB_EXPECTED_SIGNER_ARN;
  const cognitoClientId = environment.COGNITO_CLIENT_ID;
  const userPoolId = environment.COGNITO_USER_POOL_ID;
  if (
    !awsRegion ||
    !SAFE_REGION.test(awsRegion) ||
    !expectedSignerArn ||
    !cognitoClientId ||
    !userPoolId
  ) {
    throw new IdentityVerificationError();
  }
  return {
    mode,
    awsRegion,
    expectedSignerArn,
    cognitoClientId,
    cognitoIssuer: `https://cognito-idp.${awsRegion}.amazonaws.com/${userPoolId}`,
  };
}

function requiredHeader(headers: Headers, name: string): string {
  const value = headers.get(name)?.trim();
  if (!value) throw new IdentityVerificationError();
  return value;
}

async function albPublicKey(token: string, awsRegion: string): Promise<CryptoKey> {
  const protectedHeader = decodeProtectedHeader(token);
  const keyId = protectedHeader.kid;
  if (protectedHeader.alg !== "ES256" || typeof keyId !== "string" || !SAFE_KEY_ID.test(keyId)) {
    throw new IdentityVerificationError();
  }
  const cached = albCertificateCache.get(keyId);
  if (cached) return cached;

  const response = await fetch(
    `https://public-keys.auth.elb.${awsRegion}.amazonaws.com/${keyId}`,
    {
      cache: "force-cache",
      signal: AbortSignal.timeout(5_000),
    },
  );
  if (!response.ok) throw new IdentityVerificationError();
  const certificate = await response.text();
  if (
    certificate.length > CERTIFICATE_LIMIT_BYTES ||
    !certificate.startsWith("-----BEGIN PUBLIC KEY-----")
  ) {
    throw new IdentityVerificationError();
  }
  const key = await importSPKI(certificate, "ES256");
  albCertificateCache.set(keyId, key);
  return key;
}

function cognitoJwks(issuer: string) {
  const cached = cognitoJwksCache.get(issuer);
  if (cached) return cached;
  const jwks = createRemoteJWKSet(new URL(`${issuer}/.well-known/jwks.json`), {
    timeoutDuration: 5_000,
    cooldownDuration: 30_000,
    cacheMaxAge: 3_600_000,
  });
  cognitoJwksCache.set(issuer, jwks);
  return jwks;
}

function roleFromClaims(payload: JWTPayload): ChangeOpsRole {
  const groups = payload["cognito:groups"];
  if (!Array.isArray(groups)) throw new IdentityVerificationError();
  const roles = groups.filter(
    (group): group is ChangeOpsRole => typeof group === "string" && ALLOWED_ROLES.has(group),
  );
  if (roles.length !== 1 || groups.length !== 1) throw new IdentityVerificationError();
  return roles[0];
}

export async function verifiedIdentity(headers: Headers): Promise<VerifiedIdentity> {
  const config = configuration();
  if (config.mode !== "alb") {
    const actor = requiredHeader(headers, "x-changeops-actor");
    const role = requiredHeader(headers, "x-changeops-role");
    if (!ALLOWED_ROLES.has(role)) throw new IdentityVerificationError();
    return { actor, role: role as ChangeOpsRole };
  }

  try {
    const claimsToken = requiredHeader(headers, "x-amzn-oidc-data");
    const subjectHeader = requiredHeader(headers, "x-amzn-oidc-identity");
    const accessToken = requiredHeader(headers, "x-amzn-oidc-accesstoken");
    const claimsKey = await albPublicKey(claimsToken, config.awsRegion!);
    const { payload: claims, protectedHeader: claimsHeader } = await jwtVerify(
      claimsToken,
      claimsKey,
      {
        algorithms: ["ES256"],
        requiredClaims: ["sub"],
      },
    );
    const headerExpiry =
      typeof claimsHeader.exp === "number"
        ? claimsHeader.exp
        : typeof claimsHeader.exp === "string"
          ? Number(claimsHeader.exp)
          : Number.NaN;
    if (
      claimsHeader.signer !== config.expectedSignerArn ||
      claimsHeader.client !== config.cognitoClientId ||
      claimsHeader.iss !== config.cognitoIssuer ||
      !Number.isFinite(headerExpiry) ||
      headerExpiry <= Math.floor(Date.now() / 1000) ||
      claims.sub !== subjectHeader
    ) {
      throw new IdentityVerificationError();
    }

    const { payload: access } = await jwtVerify(
      accessToken,
      cognitoJwks(config.cognitoIssuer!),
      {
        algorithms: ["RS256"],
        issuer: config.cognitoIssuer,
        requiredClaims: ["exp", "iss", "sub", "client_id", "token_use"],
      },
    );
    if (
      access.sub !== subjectHeader ||
      access.client_id !== config.cognitoClientId ||
      access.token_use !== "access"
    ) {
      throw new IdentityVerificationError();
    }
    return { actor: subjectHeader, role: roleFromClaims(access) };
  } catch {
    throw new IdentityVerificationError();
  }
}

export function identityMode(): IdentityMode {
  return configuration().mode;
}

export function clearIdentityCachesForTests(): void {
  albCertificateCache.clear();
  cognitoJwksCache.clear();
}
