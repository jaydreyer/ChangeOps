const SAFE_REQUEST_ID = /^[A-Za-z0-9._:-]{1,100}$/;

export function requestId(headers: Headers): string {
  const supplied = headers.get("x-request-id")?.trim();
  return supplied && SAFE_REQUEST_ID.test(supplied) ? supplied : crypto.randomUUID();
}
