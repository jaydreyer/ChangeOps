export function flattenObject(
  value: Record<string, unknown>,
  prefix = "",
): [string, unknown][] {
  return Object.entries(value).flatMap(([key, item]) => {
    const path = prefix ? `${prefix}.${key}` : key;
    if (item && typeof item === "object" && !Array.isArray(item)) {
      return flattenObject(item as Record<string, unknown>, path);
    }
    return [[path, item]];
  });
}

export function formatValue(value: unknown) {
  return Array.isArray(value) ? value.join(", ") : String(value);
}

export function humanize(value: string) {
  return value.replaceAll("_", " ").replace(/^\w/, (letter) => letter.toUpperCase());
}

export function formatDate(value: string) {
  return new Intl.DateTimeFormat("en-US", { dateStyle: "medium", timeZone: "UTC" }).format(
    new Date(value),
  );
}

export function formatDateTime(value: string) {
  return new Intl.DateTimeFormat("en-US", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function shortIdentifier(value: string) {
  return value.length > 12 ? `${value.slice(0, 8)}…` : value;
}
