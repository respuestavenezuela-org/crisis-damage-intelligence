import { timingSafeEqual } from "node:crypto";
import type { InternalApiErrorCode } from "@/lib/api/internal-response";

export type InternalApiAuthFailure = {
  status: number;
  code: InternalApiErrorCode;
  message: string;
};

function isEnabled() {
  return process.env.INTERNAL_API_ENABLED === "true";
}

function safeTokenEquals(actual: string, expected: string) {
  const actualBuffer = Buffer.from(actual);
  const expectedBuffer = Buffer.from(expected);
  if (actualBuffer.length !== expectedBuffer.length) return false;
  return timingSafeEqual(actualBuffer, expectedBuffer);
}

export function checkInternalApiAuth(request: Request): InternalApiAuthFailure | null {
  if (!isEnabled()) {
    return {
      status: 403,
      code: "internal_api_disabled",
      message: "Internal API is disabled. Set INTERNAL_API_ENABLED=true to expose it intentionally.",
    };
  }

  const expectedToken = process.env.INTERNAL_API_TOKEN?.trim();
  const allowNoToken = process.env.INTERNAL_API_ALLOW_NO_TOKEN === "true";
  if (allowNoToken) return null;

  if (!expectedToken) {
    return {
      status: 403,
      code: "internal_api_unauthorized",
      message: "Internal API token is not configured. Set INTERNAL_API_TOKEN or explicitly set INTERNAL_API_ALLOW_NO_TOKEN=true for local contract tests.",
    };
  }

  const authorization = request.headers.get("authorization") ?? "";
  const prefix = "Bearer ";
  const suppliedToken = authorization.startsWith(prefix) ? authorization.slice(prefix.length).trim() : "";

  if (!suppliedToken || !safeTokenEquals(suppliedToken, expectedToken)) {
    return {
      status: 403,
      code: "internal_api_unauthorized",
      message: "Internal API token is missing or invalid.",
    };
  }

  return null;
}
