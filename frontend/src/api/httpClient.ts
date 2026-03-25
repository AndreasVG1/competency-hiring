import { getApiBaseUrl } from "./config";
import type { ApiErrorResponse } from "../types/domain";

type PrimitiveQueryValue = string | number | boolean | null | undefined;

interface RequestOptions {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  query?: Record<string, PrimitiveQueryValue>;
  body?: unknown;
  headers?: Record<string, string>;
  auth?: boolean;
  signal?: AbortSignal;
}

type AccessTokenResolver = () => string | null;

const apiBaseUrl = getApiBaseUrl();
let resolveAccessToken: AccessTokenResolver = () => null;

export class ApiClientError extends Error {
  statusCode: number;
  payload: ApiErrorResponse;

  constructor(statusCode: number, payload: ApiErrorResponse) {
    super(payload.details[0]?.message ?? payload.error);
    this.name = "ApiClientError";
    this.statusCode = statusCode;
    this.payload = payload;
  }
}

export function setAccessTokenResolver(resolver: AccessTokenResolver): void {
  resolveAccessToken = resolver;
}

function buildUrl(path: string, query?: Record<string, PrimitiveQueryValue>): string {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  const url = new URL(`${apiBaseUrl}${normalizedPath}`);

  if (!query) {
    return url.toString();
  }

  for (const [key, value] of Object.entries(query)) {
    if (value === undefined || value === null) {
      continue;
    }
    url.searchParams.set(key, String(value));
  }

  return url.toString();
}

function normalizeErrorPayload(payload: unknown): ApiErrorResponse {
  if (
    payload &&
    typeof payload === "object" &&
    "error" in payload &&
    typeof payload.error === "string" &&
    "details" in payload &&
    Array.isArray(payload.details)
  ) {
    return payload as ApiErrorResponse;
  }

  return {
    error: "unknown_error",
    details: [{ message: "The request failed." }],
  };
}

async function parseJsonSafe(response: Response): Promise<unknown> {
  const contentType = response.headers.get("content-type");
  if (!contentType?.includes("application/json")) {
    return null;
  }
  return response.json();
}

export async function apiRequest<TResponse>(
  path: string,
  options: RequestOptions = {},
): Promise<TResponse> {
  const requestHeaders: Record<string, string> = {
    ...(options.headers ?? {}),
  };

  if (options.auth !== false) {
    const accessToken = resolveAccessToken();
    if (accessToken) {
      requestHeaders.Authorization = `Bearer ${accessToken}`;
    }
  }

  let requestBody: string | undefined;
  if (options.body !== undefined) {
    requestHeaders["Content-Type"] = "application/json";
    requestBody = JSON.stringify(options.body);
  }

  const response = await fetch(buildUrl(path, options.query), {
    method: options.method ?? "GET",
    headers: requestHeaders,
    body: requestBody,
    signal: options.signal,
  });

  if (!response.ok) {
    const payload = normalizeErrorPayload(await parseJsonSafe(response));
    throw new ApiClientError(response.status, payload);
  }

  if (response.status === 204) {
    return undefined as TResponse;
  }

  return (await parseJsonSafe(response)) as TResponse;
}

