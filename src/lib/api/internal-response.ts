import {
  INTERNAL_API_CAVEATS,
  INTERNAL_API_SOURCE_LABELS,
  INTERNAL_API_VERSION,
} from "@/lib/api/internal-contracts";

type JsonResponseInit = ResponseInit & {
  headers?: HeadersInit;
};

export type InternalApiErrorCode =
  | "internal_api_disabled"
  | "internal_api_unauthorized"
  | "invalid_query"
  | "aoi_not_found"
  | "internal_data_invalid"
  | "internal_data_unavailable"
  | "internal_server_error";

export class InternalApiHttpError extends Error {
  readonly status: number;
  readonly code: InternalApiErrorCode;
  readonly details?: unknown;

  constructor(status: number, code: InternalApiErrorCode, message: string, details?: unknown) {
    super(message);
    this.name = "InternalApiHttpError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

function buildHeaders(headers?: HeadersInit) {
  const nextHeaders = new Headers(headers);
  if (!nextHeaders.has("Cache-Control")) {
    nextHeaders.set("Cache-Control", "no-store");
  }
  return nextHeaders;
}

function baseEnvelope() {
  return {
    version: INTERNAL_API_VERSION,
    generatedAt: new Date().toISOString(),
    sourceLabels: INTERNAL_API_SOURCE_LABELS,
    caveats: INTERNAL_API_CAVEATS,
  };
}

export function internalJson<T>(data: T, init: JsonResponseInit = {}) {
  return Response.json(
    {
      ...baseEnvelope(),
      data,
    },
    {
      ...init,
      headers: buildHeaders(init.headers),
    },
  );
}

export function internalError(
  status: number,
  code: InternalApiErrorCode,
  message: string,
  details?: unknown,
  init: JsonResponseInit = {},
) {
  return Response.json(
    {
      ...baseEnvelope(),
      error: {
        code,
        message,
        details,
      },
    },
    {
      ...init,
      status,
      headers: buildHeaders(init.headers),
    },
  );
}

export function zodDetails(issues: Array<{ path: PropertyKey[]; message: string }>) {
  return issues.slice(0, 12).map((issue) => ({
    path: issue.path.map(String).join("."),
    message: issue.message,
  }));
}
