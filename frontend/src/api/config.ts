const DEFAULT_API_BASE_URL = "http://localhost:8000";

function trimTrailingSlashes(value: string): string {
  return value.replace(/\/+$/, "");
}

export function getApiBaseUrl(): string {
  const configuredValue = import.meta.env.VITE_API_BASE_URL;
  if (typeof configuredValue !== "string" || configuredValue.trim().length === 0) {
    return DEFAULT_API_BASE_URL;
  }

  return trimTrailingSlashes(configuredValue.trim());
}

